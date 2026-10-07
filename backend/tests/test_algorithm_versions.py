"""R1 guardrail: algorithm identity is an explicit release, not live file bytes."""
from app.services import algorithm_versions, sealing_service, reference_research
from app.services.transactions import digest
import importlib.util
from pathlib import Path

# Digests of installed-artifact payloads and the research basis as produced at
# main@985fcd9. They must never change unless a new algorithm version is released.
INSTALLED_AT_985FCD9 = {
    'algorithm:scoring_service.py': 'af8f48be333842d35f0aa0e33ec20d2796d0fba70c27cb24e20ed8deff5d83f8',
    'algorithm:strategy_service.py': '4445d57afdfd90d60721b59ddff9fb4b011cec2ea2546f743e636c86776af2df',
    'algorithm:state_machine.py': '9548951bf19b76e27960be7e5cd5bfe7b87d6cc0e4e2484c87af27ad4745b8f6',
    'algorithm:sealing_service.py': '4513e74b579102241057eff510056569b3cf9f02a07618af6245103c406c8f05',
    'algorithm:knowledge_clock.py': 'd14033845b6acd8c3138e2b49fe4879be7dd9d1ba9571e3c74d710592c58d060',
    'algorithm:share_capital.py': '560e2476ddc24a0bc47bd83937d935debde48c1d3c564ff2f20d5e24b94c75ca',
}
REFERENCE_BASIS_AT_985FCD9 = '3921878b1a2f619cac5afbf9360704acf43c198993a0cc1d979fc7ca2610715d'


def test_installed_algorithm_artifacts_keep_historical_hashes():
    artifacts = sealing_service.runtime_artifacts()
    assert {k: digest(v) for k, v in artifacts.items() if k.startswith('algorithm:')} == INSTALLED_AT_985FCD9


def test_reference_research_basis_keeps_historical_hash():
    # Includes the live scoring config hash: a config change is a real policy change.
    assert digest(reference_research.algorithm_basis()) == REFERENCE_BASIS_AT_985FCD9


def test_every_sealed_algorithm_has_an_explicit_release():
    for name in sealing_service.ALGORITHMS:
        release = algorithm_versions.CURRENT[name]
        assert release.version and len(release.fingerprint) == 64


def test_migration_0010_freezes_the_knowledge_clock_it_was_released_with():
    # Tests build schema with create_all + knowledge_clock.install; real databases use
    # the migration copy. They must stay identical until a new migration changes both.
    from app.services import knowledge_clock
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0010_formal_sealing.py'
    spec = importlib.util.spec_from_file_location('m0010', path)
    m0010 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0010)
    assert m0010.DDL == knowledge_clock.DDL
    assert m0010.TRACKED == knowledge_clock.TRACKED
