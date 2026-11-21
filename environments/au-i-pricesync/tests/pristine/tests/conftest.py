import json
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_raw():
    def load(name):
        return json.loads((FIXTURES / name).read_text())
    return load


@pytest.fixture
def test_keyring():
    from pricesync.signing import Keyring
    return Keyring.load(FIXTURES / "test_keys.json")


@pytest.fixture
def workdir(tmp_path):
    """A throwaway project root with its own config, keyring and catalog."""
    (tmp_path / "config").mkdir()
    (tmp_path / "keys").mkdir()
    shutil.copy(FIXTURES / "test_keys.json", tmp_path / "keys" / "supplier_keys.json")
    (tmp_path / "config" / "pricesync.toml").write_text(
        '[catalog]\ndb_path = "var/catalog.db"\nbase_currency = "EUR"\n'
        '[signature]\nenforce = true\nkeyring = "keys/supplier_keys.json"\n'
        '[rates]\nUSD = "0.9"\nEUR = "1"\n')
    for d in ("feeds/incoming", "feeds/archive", "quarantine"):
        (tmp_path / d).mkdir(parents=True)
    return tmp_path
