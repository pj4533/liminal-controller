# Local speech artifacts

whisper.cpp v1.9.5, CPU-only x86_64-v3/AVX2, GNU2.35 target, statically linked
ggml backends, OpenMP/GPU/CURL off. Compiled with verified Zig0.13.0 and CMake;
use the existing /lib/ld-linux-x86-64.so.2 loader. Existing device research measured
base.en30-second actual DTW at6.16seconds,1,453,616KiB peak RSS, one inference
thread. These are isolated research results, not concurrent-audio acceptance.
The i3-1115G4/AVX2, approximately7.4GiB device can run it; speech is never in the
real-time renderer.

Private build inputs live in .build/speech and are excluded from git. Obtain
and verify them through the approved artifact process; runtime never downloads.
Run python3 scripts/check-speech-artifacts.py before staging.

| Artifact | SHA256 |
| --- | --- |
| whisper-cli | bee176f0edafd2cc2c563cb8d73c611bcffb8dfe7af40465ea8c2c6e25fe51ab |
| ggml-base.en.bin | a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002 |
| averaged_perceptron_tagger_eng.zip | 6025f530624335c67d6547d44757b357b4e79bae030a0383e9887a92c1718f0b |

Primary sources: [whisper.cpp v1.9.5](https://github.com/ggml-org/whisper.cpp/tree/v1.9.5),
[model manifest](https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/models/README.md),
[OpenAI Whisper](https://github.com/openai/whisper),
[NLTK model metadata](https://github.com/nltk/nltk_data/blob/gh-pages/packages/taggers/averaged_perceptron_tagger_eng.xml),
[NLTK perceptron](https://www.nltk.org/api/nltk.tag.perceptron.html).
Whisper code/models and the tagger/model are MIT licensed; packaging includes
copyright notices, model metadata and decoder licenses under licenses/.
Only the adapted inference methods are copied; no NLTK runtime installation or
network model discovery is performed. NLTK POS does not provide named entities.
