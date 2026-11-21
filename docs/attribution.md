# Attribution

- The PeSTO numerical piece values and piece-square tables are from Ronald
  Friederich's Rofchade parameters as reproduced on the Chess Programming
  Wiki. The wiki credits its contributors, including Gerd Isenberg, and
  credits Paweł Koziol's TSCP-based reference implementation. The data here
  have been reformatted into C++14 arrays indexed by phase and piece type with
  a leading empty-piece row. The adapted tables are distributed under
  [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
  [Wiki source](https://chessprogramming.org/PeSTO%27s_Evaluation_Function) ·
  [Original parameter post](https://www.talkchess.com/forum3/viewtopic.php?f=2&start=19&t=68311) ·
  [PeSTO author's article](https://rofchade.nl/?p=307)
- Standard perft FENs and counts are reference test data. The benchmark opening
  lines are conventional chess moves and the tactical suite uses hand-built
  positions. [Perft reference](https://www.chessprogramming.org/Perft_Results)
- The board, evaluation implementation, search, firmware, tests and
  benchmark harness were written for this project. See [LICENSE](../LICENSE).
