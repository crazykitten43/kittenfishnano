#include "micro.hpp"
#ifdef MICRO_NNUE_HEADER
#include MICRO_NNUE_HEADER
#endif
#ifdef NANO_TOURNAMENT
#include "nnue.hpp"
namespace net0 {
#include "../results/nnue/l4-20261121/large/704x128/int8.hpp"
}
namespace net1 {
#include "../results/nnue/l4-20261121/large/704x128/int16.hpp"
}
namespace net2 {
#include "../results/nnue/l4-20261121/large/768x256/int8.hpp"
}
namespace net3 {
#include "../results/nnue/l4-20261121/large/768x256/int16.hpp"
}
#endif
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/resource.h>

using namespace micro;
namespace {
constexpr size_t ttEntries=16384, pawnEntries=512;
TTEntry table[ttEntries]{};
PawnEntry pawns[pawnEntries]{};
Hce hce{0,pawns,pawnEntries};
uint64_t now() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}
Search engine({Hce::call,&hce},table,ttEntries,now);
#ifdef MICRO_NNUE_HEADER
ExportedNnue nnue(exportedWeights);
Search nnueEngine(nnue.evaluator(),table,ttEntries,now);
#endif
Search& selectEngine(unsigned flags, const Board& board) {
#ifdef MICRO_NNUE_HEADER
    if (flags == 64) {
        nnue.refresh(board);
        return nnueEngine;
    }
#else
    (void)board;
#endif
#ifdef NANO_TOURNAMENT
    static net0::ExportedNnue n0(net0::exportedWeights);
    static net1::ExportedNnue n1(net1::exportedWeights);
    static net2::ExportedNnue n2(net2::exportedWeights);
    static net3::ExportedNnue n3(net3::exportedWeights);
    static Search s0(n0.evaluator(),table,ttEntries,now);
    static Search s1(n1.evaluator(),table,ttEntries,now);
    static Search s2(n2.evaluator(),table,ttEntries,now);
    static Search s3(n3.evaluator(),table,ttEntries,now);
    switch (flags) {
        case 64: n0.refresh(board); return s0;
        case 65: n1.refresh(board); return s1;
        case 66: n2.refresh(board); return s2;
        case 67: n3.refresh(board); return s3;
    }
#endif
    hce.flags=flags;
    return engine;
}
volatile int64_t sink;
struct Position { std::string group, name, fen, targets; Board board; };

std::vector<Position> readPositions(const char* path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("Cannot open position suite");
    std::vector<Position> positions;
    std::string line;
    while (std::getline(in,line)) {
        if (line.empty() || line[0]=='#') continue;
        Position p;
        std::istringstream row(line);
        std::getline(row,p.group,'\t');
        std::getline(row,p.name,'\t');
        std::getline(row,p.fen,'\t');
        std::getline(row,p.targets);
        if (!p.board.load(p.fen.c_str())) throw std::runtime_error("Bad FEN: "+p.name);
        std::istringstream targets(p.targets);
        std::string target;
        while (targets>>target)
            if (!parseMove(p.board,target.c_str())) throw std::runtime_error("Bad tactic: "+p.name);
        positions.push_back(p);
    }
    if (positions.empty()) throw std::runtime_error("Empty position suite");
    return positions;
}
unsigned mask(const char* value) {
    auto flags=std::stoul(value);
#ifdef MICRO_NNUE_HEADER
    if (flags==64) return 64;
#endif
#ifdef NANO_TOURNAMENT
    if (flags>=64 && flags<=67) return unsigned(flags);
#endif
    if (flags>63) throw std::runtime_error("Feature mask must be in [0, 63]");
    return unsigned(flags);
}
void performance(unsigned flags,int millis,const char* path) {
    auto positions=readPositions(path);
    hce.flags=flags;
    // Eight sweeps between clock reads. Rotate over the entire suite.
    int64_t checksum=0;
    uint64_t evals=0, start=now(), elapsed;
    do {
        for (int sweep=0;sweep<8;++sweep)
            for (const auto& p : positions) {
                auto& selected=selectEngine(flags,p.board);
#ifdef MICRO_NNUE_HEADER
                if (&selected == &nnueEngine) {
                    checksum+=nnue.output(p.board.side);
                    continue;
                }
#else
                (void)selected;
#endif
                checksum+=hce.evaluate(p.board);
            }
        evals+=8*positions.size();
        elapsed=now()-start;
    } while (elapsed<200000);
    sink=checksum;
    std::cout<<"eval,"<<flags<<','<<evals<<','<<elapsed<<','<<checksum<<'\n';
    for (auto& p : positions) {
        auto& selected=selectEngine(flags,p.board);
        selected.clear();
        std::fill_n(pawns,pawnEntries,PawnEntry{});
        auto begin=now();
        auto result=selected.run(p.board,{millis,32});
        auto micros=now()-begin;
        char name[6];
        notation(result.move,name);
        int solved=-1;
        if (!p.targets.empty()) {
            solved=0;
            std::istringstream moves(p.targets);
            std::string accepted;
            while (moves>>accepted)
                if (accepted==name) solved=1;
        }
        std::cout<<"search,"<<flags<<','<<p.group<<','<<p.name<<','<<result.nodes<<','<<micros<<','
                 <<result.depth<<','<<name<<','<<result.score<<','<<solved<<'\n';
    }
    rusage usage{};
    getrusage(RUSAGE_SELF,&usage);
    long rss=usage.ru_maxrss;
#ifndef __APPLE__
    rss*=1024;
#endif
    std::cout<<"memory,"<<flags<<','<<sizeof(Board)<<','<<sizeof(Search)<<','<<sizeof(table)
             <<','<<sizeof(pawns)<<','<<rss<<'\n';
}
bool legal(Board& b) {
    Moves moves;
    b.generate(moves);
    for (int i=0;i<moves.size;++i) {
        Undo u;
        if (!b.make(moves.list[i],u)) continue;
        b.unmake(moves.list[i],u);
        return true;
    }
    return false;
}
void match(unsigned first,unsigned second,int millis,int pairs,int cap,const char* path,
           int selectedColor=-1, int64_t initial=0, int64_t increment=0) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("Cannot open opening suite");
    std::string line;
    for (int pair=0;pair<pairs;++pair) {
        if (!std::getline(in,line)) throw std::runtime_error("Opening suite too short");
        std::istringstream row(line);
        std::string id;
        row>>id;
        Board opening;
        opening.load(Start);
        std::vector<uint64_t> baseHistory;
        std::string coordinate;
        while (row>>coordinate) {
            auto m=parseMove(opening,coordinate.c_str());
            Undo u;
            baseHistory.push_back(opening.key);
            if (!m || !opening.make(m,u)) throw std::runtime_error("Bad opening "+id);
        }
        for (int color=0;color<2;++color) {
            if (selectedColor!=-1 && color!=selectedColor) continue;
            int64_t clocks[2]={initial,initial};
            std::vector<int64_t> elapsed;
            Board b=opening;
            auto history=baseHistory;
            int outcome=0, plies=0;
            std::string reason="ply-cap", moves;
            for (; ; ++plies) {
                if (!legal(b)) {
                    if (b.check()) outcome=b.side==color ? -1 : 1;
                    reason=b.check() ? "mate" : "stalemate";
                    break;
                }
                if (b.dead()) { reason="dead-material"; break; }
                if (b.halfmove>=100) { reason="50-move"; break; }
                size_t previous=std::min(size_t(b.halfmove),history.size());
                if (std::count(history.end()-previous,history.end(),b.key)>=2) {
                    reason="repetition";
                    break;
                }
                if (plies+(initial ? int(baseHistory.size()) : 0)>=cap) break;
                const auto turnStart=now();
                const auto side=b.side;
                auto& selected=selectEngine(b.side==color ? first : second,b);
                selected.clear();
                std::fill_n(pawns,pawnEntries,PawnEntry{});
                int budget=millis;
                if (initial) {
                    constexpr int64_t reserve=50000;
                    budget=int(std::max(int64_t(1),std::min(clocks[side]/24+increment*3/4,
                                                       clocks[side]-reserve)/1000));
                }
                auto result=selected.run(b,{budget,32},history.data(),history.size());
                if (!result.move) throw std::runtime_error("No legal move from search");
                Undo u;
                history.push_back(b.key);
                if (!b.make(result.move,u)) throw std::runtime_error("Illegal move from search");
                if (initial) {
                    elapsed.push_back(int64_t(now()-turnStart));
                    clocks[side]-=elapsed.back();
                    if (clocks[side]<=0) {
                        clocks[side]=0;
                        outcome=side==color ? -1 : 1;
                        reason="time-forfeit";
                        break;
                    }
                    clocks[side]+=increment;
                }
                char text[6];
                notation(result.move,text);
                if (!moves.empty()) moves+=' ';
                moves+=text;
            }
            std::cout<<first<<','<<second<<','<<id<<','<<(color==White ? 'W' : 'B')
                     <<','<<outcome<<','<<reason<<','<<plies<<','<<moves;
            if (initial) {
                std::cout<<','<<clocks[White]<<','<<clocks[Black]<<',';
                for (size_t i=0;i<elapsed.size();++i)
                    std::cout<<(i ? " " : "")<<elapsed[i];
            }
            std::cout<<std::endl;
        }
    }
}
}

int main(int argc,char** argv) try {
    if (argc==5 && std::string(argv[1])=="bench") {
        performance(mask(argv[2]),std::stoi(argv[3]),argv[4]);
    } else if (argc==8 && std::string(argv[1])=="match") {
        match(mask(argv[2]),mask(argv[3]),std::stoi(argv[4]),std::stoi(argv[5]),
              std::stoi(argv[6]),argv[7]);
    } else if (argc==9 && std::string(argv[1])=="clock-match") {
        auto initial=std::stoll(argv[4]), increment=std::stoll(argv[5]);
        int cap=std::stoi(argv[6]), color=std::stoi(argv[7]);
        if (initial<=0 || increment<0 || cap<=0 || (color!=0 && color!=1))
            throw std::runtime_error("Invalid clock-match settings");
        match(mask(argv[2]),mask(argv[3]),0,1,cap,argv[8],color,initial*1000,increment*1000);
    } else if (argc==5 && std::string(argv[1])=="think") {
        Board b;
        if (!b.load(argv[4])) throw std::runtime_error("Invalid FEN");
        auto& selected=selectEngine(mask(argv[2]),b);
        auto result=selected.run(b,{std::stoi(argv[3]),32});
        char move[6];
        notation(result.move,move);
        std::cout<<move<<" score "<<result.score<<" depth "<<result.depth<<" nodes "<<result.nodes<<'\n';
    } else {
        std::cerr<<"Usage: kittenfishmicro bench MASK MS SUITE\n"
                 <<"       kittenfishmicro match MASK MASK MS PAIRS PLY_CAP OPENINGS\n"
                 <<"       kittenfishmicro clock-match MASK MASK INITIAL_MS INCREMENT_MS PLY_CAP FIRST_COLOR OPENING\n"
                 <<"       kittenfishmicro think MASK MS 'FEN'\n";
        return 2;
    }
    return 0;
} catch (const std::exception& e) {
    std::cerr<<e.what()<<'\n';
    return 1;
}
