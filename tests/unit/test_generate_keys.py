import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from security.generate_keys import generate_rsa_keypair

def test_generate_rsa_keypair(tmp_path):
    with patch("security.generate_keys.KEYS_DIR", tmp_path):
        generate_rsa_keypair(bits=1024)  # use 1024 for faster tests
        
        priv_path = tmp_path / "private.pem"
        pub_path = tmp_path / "public.pem"
        
        assert priv_path.exists()
        assert pub_path.exists()
        
        priv_content = priv_path.read_text()
        assert "BEGIN PRIVATE KEY" in priv_content
        
        pub_content = pub_path.read_text()
        assert "BEGIN PUBLIC KEY" in pub_content
