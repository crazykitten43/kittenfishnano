#include "micro.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>

using namespace micro;
#define REQUIRE(cond) do { if (!(cond)) { std::fprintf(stderr,"%d: %s\n",__LINE__,#cond); std::exit(1); } } while (0)

namespace {
constexpr char kiwipete[]="r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1";
constexpr char endgame[]="8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1";
constexpr char promotion[]="r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1";
constexpr char checks[]="rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8";
constexpr char middle[]="r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10";

bool same(const Board& a,const Board& b) {
    return !std::memcmp(a.square,b.square,sizeof a.square) &&
           !std::memcmp(a.pieces,b.pieces,sizeof a.pieces) &&
           a.key==b.key && a.pawnKey==b.pawnKey && a.mg==b.mg && a.eg==b.eg &&
           a.material==b.material && a.phase==b.phase && a.king[0]==b.king[0] &&
           a.king[1]==b.king[1] && a.side==b.side && a.rights==b.rights &&
           a.ep==b.ep && a.halfmove==b.halfmove;
}
void reversible(Board& b,int depth) {
    if (!depth) return;
    Board original=b;
    Moves moves;
    b.generate(moves);
    for (int i=0;i<moves.size;++i) {
        Undo u;
        if (b.make(moves.list[i],u)) {
            reversible(b,depth-1);
            b.unmake(moves.list[i],u);
        }
        REQUIRE(same(b,original));
    }
}
void transition(const char* before,const char* move,const char* after) {
    Board b, expected;
    REQUIRE(b.load(before));
    REQUIRE(expected.load(after));
    Board copy=b;
    auto m=parseMove(b,move);
    Undo u;
    REQUIRE(m && b.make(m,u) && same(b,expected));
    b.unmake(m,u);
    REQUIRE(same(b,copy));
}
struct EvalTrace {
    uint64_t keys[MaxPly]{};
    int depth=0, pushes=0;
    Hce hce{Variants[3]};
    static int score(const Board& b,void* context) {
        auto& trace=*static_cast<EvalTrace*>(context);
        REQUIRE(trace.keys[trace.depth]==b.key);
        return trace.hce.evaluate(b);
    }
    static void push(const Board& child,Move,const Undo& u,void* context) {
        auto& trace=*static_cast<EvalTrace*>(context);
        REQUIRE(trace.keys[trace.depth]==u.key);
        REQUIRE(trace.depth+1<MaxPly);
        trace.keys[++trace.depth]=child.key;
        ++trace.pushes;
    }
    static void pop(const Board& child,Move,const Undo& u,void* context) {
        auto& trace=*static_cast<EvalTrace*>(context);
        REQUIRE(trace.depth>0 && trace.keys[trace.depth]==child.key);
        REQUIRE(trace.keys[--trace.depth]==u.key);
    }
};
}

int main() {
    struct Perft { const char* fen; uint64_t counts[4]; };
    const Perft suite[]={
        {Start,{20,400,8902,197281}},
        {kiwipete,{48,2039,97862,4085603}},
        {endgame,{14,191,2812,43238}},
        {promotion,{6,264,9467,422333}},
        {checks,{44,1486,62379,2103487}},
        {middle,{46,2079,89890,3894594}}
    };
    Board b;
    for (const auto& item : suite) {
        REQUIRE(b.load(item.fen));
        for (int d=1;d<=4;++d) {
            auto got=perft(b,d);
            std::printf("perft %d %llu\n",d,static_cast<unsigned long long>(got));
            REQUIRE(got==item.counts[d-1]);
        }
        reversible(b,2);
    }
    transition(Start,"e2e4",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1");
    transition("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","e5d6",
        "4k3/8/3P4/8/8/8/8/4K3 b - - 0 1");
    transition("4k2r/6P1/8/8/8/8/8/4K3 w k - 0 1","g7h8n",
        "4k2N/8/8/8/8/8/8/4K3 b - - 0 1");
    transition("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1","e8c8",
        "2kr3r/8/8/8/8/8/8/R3K2R w KQ - 1 2");
    REQUIRE(b.load("4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1"));
    Board copy=b;
    REQUIRE(!parseMove(b,"e5d6") && same(b,copy));
    REQUIRE(b.load("4r1k1/8/8/3pP3/8/8/8/4K3 w - - 0 1"));
    REQUIRE(copy.key==b.key);
    REQUIRE(b.load("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"));
    copy=b;
    REQUIRE(b.load("4k3/8/8/3pP3/8/8/8/4K3 w - - 0 1"));
    REQUIRE(copy.key!=b.key && copy.pawnKey==b.pawnKey);
    REQUIRE(b.load("4kr2/8/8/8/8/8/8/R3K2R w KQ - 0 1"));
    REQUIRE(!parseMove(b,"e1g1") && parseMove(b,"e1c1"));
    transition("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","a1a8",
        "R3k2r/8/8/8/8/8/8/4K2R b Kk - 0 1");
    REQUIRE(!b.load("8/8/8/8/8/8/8/8 w - -"));
    REQUIRE(!b.load("4k3/8/8/8/8/8/8/4K3 w - a"));
    REQUIRE(b.load("4k3/8/8/8/8/8/8/4K3 w - - 0 1") && b.dead());
    static TTEntry tt[1024]{};
    for (auto flags : Variants) {
        Hce h{flags};
        PawnEntry entry[1]{};
        Hce cached{flags,entry,1};
        Board flipped;
        REQUIRE(b.load("r3k2r/pp1p1p2/2n1b1p1/2pPp2p/1P2P3/2P2N1P/P4PP1/R3K2R w KQkq - 0 1"));
        REQUIRE(flipped.load("r3k2r/p4pp1/2p2n1p/1p2p3/2PpP2P/2N1B1P1/PP1P1P2/R3K2R b KQkq - 0 1"));
        REQUIRE(h.evaluate(b)==h.evaluate(flipped));
        REQUIRE(h.evaluate(b)==cached.evaluate(b));
        REQUIRE(h.evaluate(b)==cached.evaluate(b));
        Search s({Hce::call,&h},tt,1024,nullptr);
        s.clear();
        REQUIRE(b.load("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"));
        auto draw=s.run(b,{0,3});
        REQUIRE(!draw.move && draw.score==0);
        REQUIRE(b.load("7k/6Q1/6K1/8/8/8/8/8 b - - 100 1"));
        REQUIRE(s.run(b,{0,3}).score==-Mate);
        REQUIRE(b.load("7k/8/5KQ1/8/8/8/8/8 w - - 0 1"));
        auto mate=s.run(b,{0,2});
        REQUIRE(mate.score==Mate-1);
        REQUIRE(b.load(Start));
        copy=b;
        REQUIRE(s.run(b,{0,9,100}).move && same(b,copy));
        REQUIRE(b.load("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 8 5"));
        uint64_t history[4]={b.key,1,b.key,2};
        REQUIRE(s.run(b,{0,4},history,4).score==0);
    }
    REQUIRE(b.load(kiwipete));
    copy=b;
    EvalTrace trace;
    trace.keys[0]=b.key;
    Search traced({EvalTrace::score,&trace,EvalTrace::push,EvalTrace::pop},nullptr,0,nullptr);
    auto stopped=traced.run(b,{0,12,3000});
    REQUIRE(stopped.nodes==3000 && stopped.move && trace.depth==0 && trace.pushes>0);
    REQUIRE(same(b,copy));
    std::puts("All correctness tests passed");
}
