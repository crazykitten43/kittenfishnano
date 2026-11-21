#pragma once

namespace nano_experiment {

enum Feature : unsigned {
    Pvs = 1u << 0,
    TableMoves = 1u << 1,
    TableBounds = 1u << 2,
    Killers = 1u << 3,
    CaptureOrder = 1u << 4,
    Quiescence = 1u << 5,
    Aspiration = 1u << 6,
    LateReduction = 1u << 7,
    CheckExtension = 1u << 8,
    ReverseFutility = 1u << 9,
};

enum Profile : unsigned {
    Baseline = Pvs | TableMoves | TableBounds | Killers | CaptureOrder | Quiescence,
    AlphaBeta = Baseline & ~Pvs,
    NoTable = Baseline & ~(TableMoves | TableBounds),
    TableOrderingOnly = Baseline & ~TableBounds,
    NoKillers = Baseline & ~Killers,
    NoCaptureOrdering = Baseline & ~CaptureOrder,
    GeneratorOrder = Baseline & ~(TableMoves | Killers | CaptureOrder),
    StaticLeaves = Baseline & ~Quiescence,
    PlainNegamax = StaticLeaves & ~(Pvs | TableMoves | TableBounds | Killers | CaptureOrder),
    AspirationPvs = Baseline | Aspiration,
    LateMoveReductions = Baseline | LateReduction,
    ExtendChecks = Baseline | CheckExtension,
    ReverseFutilityPruning = Baseline | ReverseFutility,
    QuietPruning = Baseline | LateReduction | ReverseFutility,
    AspirationLmr = Baseline | Aspiration | LateReduction,
    SelectivePvs = Baseline | Aspiration | LateReduction | CheckExtension | ReverseFutility,
};

#ifndef NANO_SEARCH_PROFILE
#define NANO_SEARCH_PROFILE Baseline
#endif

constexpr bool enabled(Feature flag) {
    return (Profile::NANO_SEARCH_PROFILE & flag) != 0;
}

}
