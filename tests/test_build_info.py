"""Build info endpoint tests."""
import os, sys, tempfile, unittest, json, threading, http.server
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import server


class BuildInfoTestCase(unittest.TestCase):
    def test_env_var(self):
        os.environ["CLIENT_CONFIG_BUILD_VERSION"] = "feat/t_afaafd77-build-identity"
        try:
            self.assertEqual(server.build_version(), "feat/t_afaafd77-build-identity")
        finally:
            del os.environ["CLIENT_CONFIG_BUILD_VERSION"]

    def test_fallback_unknown(self):
        os.environ.pop("CLIENT_CONFIG_BUILD_VERSION", None)
        os.environ.pop("BUILD_VERSION", None)
        import subprocess
        expected = subprocess.check_output(["git","rev-parse","HEAD"], cwd=str(Path(__file__).resolve().parents[1]), text=True).strip()
        self.assertEqual(server.build_version(), expected)

    def test_endpoint(self):
        os.environ["CLIENT_CONFIG_BUILD_VERSION"] = "t_afaafd77"
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        port = httpd.server_port
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/build-info") as r:
                data = json.loads(r.read())
            self.assertEqual(data["build_id"], "t_afaafd77")
        finally:
            httpd.shutdown()
            os.environ.pop("CLIENT_CONFIG_BUILD_VERSION", None)


if __name__ == "__main__":
    unittest.main()
