"""Explicit, released algorithm versions.

Before R1 an algorithm's identity was the sha256 of its source file, read live from
disk. Any edit, even reformatting or a comment, changed every installed artifact,
frozen manifest and research basis hash, so the code could not be refactored safely.

Now each algorithm has a released version, and its fingerprint is the source sha256
recorded *when that version was released* (main@985fcd9 for v1). Installed artifacts
and research bases carry that recorded fingerprint, so hashes are unchanged for
existing databases and stay stable across pure refactors.

Releasing changed behaviour (anything that can change a score, state, PE or manifest):
1. add a new entry with a bumped version and a fresh fingerprint
   (``sha256sum backend/app/domains/<domain>/<file>``) and point CURRENT at it;
2. keep the old entries, they identify historical manifests;
3. run the approved install_artifacts release step so the new artifact is known
   before the next cutoff.
Behaviour is protected by the fixed-input regression tests, not by file bytes.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Release:
    file: str
    version: str
    fingerprint: str  # source sha256 recorded at release time, never recomputed
    released_at_commit: str


RELEASES = (
    Release('scoring_service.py', 'scoring-v1', 'ef3de324f042ea456232b9a8b68bf404fe5bbc300a9ec87ea884a9203751c22c', '985fcd9'),
    Release('strategy_service.py', 'strategy-v1', '38fa66676c43f6fb6d119da6560614191fb8e329264786b64ab2e56defae10c7', '985fcd9'),
    Release('state_machine.py', 'state-machine-v1', '11b019079aebcdb3ef2e87cc05ae92c50b5f38f3f584cde66b2ae151cdd7e0b0', '985fcd9'),
    Release('sealing_service.py', 'sealing-v1', 'cb927a4ed8681e6409e07b38d4592cbfe5691d1c78acea8e3de558d4dfa0748d', '985fcd9'),
    Release('knowledge_clock.py', 'knowledge-clock-v1', '2ff16092669c73a87892aa314bf8dbe80e95e5b47c3a1df6757053747f76821a', '985fcd9'),
    Release('share_capital.py', 'share-capital-v1', '63d8eeb4784d821385af8fc6ad0d5ef249adbaff95b5f065c6d0a56bd6a93cb3', '985fcd9'),
    Release('reference_research.py', 'reference-research-v1', '420917bd9906ba78bc7d7ef62336cee1adb944f7668ffbf6540ff0feee3010f5', '985fcd9'),
    Release('ecb_fx.py', 'ecb-fx-v1', 'eccec631d77adedd000a78798f118898ef66b57c8a715f2204b40549cf676274', '985fcd9'),
)

# The version each algorithm currently runs as.
CURRENT = {r.file: r for r in RELEASES}


def fingerprint(file):
    return CURRENT[file].fingerprint


def version(file):
    return CURRENT[file].version
