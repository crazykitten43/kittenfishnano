#include MICRO_NNUE_HEADER
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace micro;
namespace {
struct Position { Board board; int expected; };
struct Transition { Board child; Move move; Undo undo; };
volatile int64_t sink = 0;
void observe(const ExportedNnue& net) {
    // Ensure accumulator writes remain observable without scanning the state.
    asm volatile("" : : "g"(&net) : "memory");
}

bool legalTransition(const Board& board, Move move, Transition& t) {
    t.child = board;
    t.move = move;
    return t.child.make(move, t.undo);
}

template<class Operation>
void measure(const char* name, size_t size, int operationsPerPosition, Operation operation) {
    using namespace std::chrono;
    auto start = steady_clock::now();
    size_t iterations = 0;
    int64_t checksum = 0;
    double seconds;
    do {
        for (int repeat = 0; repeat < 8; ++repeat)
            for (size_t i = 0; i < size; ++i) checksum += operation(i);
        iterations += 8 * size;
        seconds = duration<double>(steady_clock::now() - start).count();
    } while (seconds < .3);
    sink = checksum;
    size_t operations = iterations * operationsPerPosition;
    std::cout << name << ',' << operations << ',' << seconds << ','
              << operations / seconds << ',' << checksum << '\n';
}
}

int main(int argc, char** argv) try {
    if (argc != 3) throw std::runtime_error("Expected fixture.tsv and quantization width");
    bool int8 = std::string(argv[2]) == "8";
    std::ifstream fixture(argv[1]);
    std::vector<Position> positions;
    std::string line;
    while (std::getline(fixture, line)) {
        auto a = line.find('\t'), b = line.find('\t', a + 1);
        Position p;
        p.expected = std::stoi(int8 ? line.substr(0, a) : line.substr(a + 1, b - a - 1));
        if (!p.board.load(line.c_str() + b + 1)) throw std::runtime_error("Invalid fixture FEN");
        positions.push_back(p);
    }
    if (positions.empty()) throw std::runtime_error("Empty fixture");

    ExportedNnue incremental(exportedWeights), refreshed(exportedWeights);
    auto hooks = incremental.evaluator();
    int validatedTransitions = 0;
    auto verify = [&](const Board& parent, const Transition& t) {
        incremental.refresh(parent);
        hooks.push(t.child, t.move, t.undo, hooks.context);
        refreshed.refresh(t.child);
        if (!incremental.sameState(refreshed)) throw std::runtime_error("Incremental push mismatch");
        hooks.pop(t.child, t.move, t.undo, hooks.context);
        refreshed.refresh(parent);
        if (!incremental.sameState(refreshed)) throw std::runtime_error("Incremental pop mismatch");
        ++validatedTransitions;
    };
    std::vector<Transition> transitions;
    for (const Position& p : positions) {
        refreshed.refresh(p.board);
        const int got = refreshed.output(p.board.side);
        if (got != p.expected)
            throw std::runtime_error("Integer parity mismatch " + std::to_string(got) +
                                     " vs " + std::to_string(p.expected));
        Moves moves;
        p.board.generate(moves);
        int representative = -1;
        for (int i = 0; i < moves.size; ++i) {
            Transition t;
            if (!legalTransition(p.board, moves.list[i], t)) continue;
            verify(p.board, t);
            if (representative < 0 || i == int(transitions.size() % moves.size)) {
                representative = i;

            }
        }
        if (representative >= 0) {
            Transition t;
            if (!legalTransition(p.board, moves.list[representative], t))
                throw std::runtime_error("Invalid benchmark move");
            transitions.push_back(t);
        }
    }
    const char* special[] = {
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
    };
    for (const char* fen : special) {
        Board b;
        if (!b.load(fen)) throw std::runtime_error("Invalid special fixture");
        Moves moves;
        b.generate(moves);
        for (int i = 0; i < moves.size; ++i) {
            Transition t;
            if (legalTransition(b, moves.list[i], t)) verify(b, t);
        }
    }

    std::cout << "parity_cases," << positions.size() << "\ntransition_cases," << validatedTransitions
              << "\nmodel_bytes," << sizeof(ExportedModel) << "\nstate_bytes," << sizeof(ExportedNnue)
              << "\nmetric,operations,seconds,operations_per_second,checksum\n";
    std::vector<ExportedNnue> ready(positions.size(), ExportedNnue(exportedWeights));
    for (size_t i = 0; i < positions.size(); ++i) ready[i].refresh(positions[i].board);
    std::vector<ExportedNnue> pending(transitions.size(), ExportedNnue(exportedWeights));
    for (size_t i = 0; i < transitions.size(); ++i) {
        auto parent = transitions[i].child;
        parent.unmake(transitions[i].move, transitions[i].undo);
        pending[i].refresh(parent);
    }
    if (pending.empty()) throw std::runtime_error("No legal transitions");
    measure("refresh", positions.size(), 1, [&](size_t i) {
        refreshed.refresh(positions[i].board);
        observe(refreshed);
        return 0;
    });
    measure("incremental_push_pop", transitions.size(), 2, [&](size_t i) {
        auto e = pending[i].evaluator();
        const auto& t = transitions[i];
        e.push(t.child, t.move, t.undo, e.context);
        observe(pending[i]);
        e.pop(t.child, t.move, t.undo, e.context);
        observe(pending[i]);
        return 0;
    });
    measure("incremental_and_output_push_pop", transitions.size(), 1, [&](size_t i) {
        auto e = pending[i].evaluator();
        const auto& t = transitions[i];
        e.push(t.child, t.move, t.undo, e.context);
        auto score = pending[i].output(t.child.side);
        e.pop(t.child, t.move, t.undo, e.context);
        observe(pending[i]);
        return score;
    });
    measure("output", positions.size(), 1, [&](size_t i) {
        return ready[i].output(positions[i].board.side);
    });
    measure("refresh_and_output", positions.size(), 1, [&](size_t i) {
        refreshed.refresh(positions[i].board);
        return refreshed.output(positions[i].board.side);
    });
    return 0;
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
