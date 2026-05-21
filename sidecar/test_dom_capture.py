import json
import unittest
import urllib.request
import threading
import time


class TestDomEventsTable(unittest.TestCase):
    def test_table_exists(self):
        import db
        conn = db._get_conn()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dom_events'"
        )
        self.assertIsNotNone(cur.fetchone(), "dom_events table should exist")

    def test_insert_and_query(self):
        import db
        events = [
            {
                "type": "click",
                "url": "https://example.com",
                "timestamp": "2024-01-01T00:00:00Z",
                "selector": "#btn",
                "element_tag": "button",
                "element_id": "btn",
                "element_class": "",
                "element_text": "OK",
                "value": "",
                "key": "",
                "x": 100,
                "y": 200,
                "session_id": "test-session-dom",
            }
        ]
        db.insert_dom_events(events)
        rows = db.get_dom_events_by_session("test-session-dom")
        self.assertTrue(any(r.get("selector") == "#btn" for r in rows))


class TestHTTPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start HTTP server in background thread
        import db
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        from http.server import HTTPServer
        import main as _main
        cls._server = HTTPServer(("127.0.0.1", 17834), _main._HTTPHandler)
        t = threading.Thread(target=cls._server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()

    def test_get_status(self):
        with urllib.request.urlopen("http://127.0.0.1:17834/status", timeout=3) as r:
            data = json.loads(r.read())
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("version"), "1.0.0")

    def test_post_dom_events(self):
        import db
        payload = json.dumps({
            "events": [{
                "type": "click",
                "url": "https://test.com",
                "timestamp": "2024-01-01T00:00:00Z",
                "selector": ".link",
                "element_tag": "a",
                "element_id": "",
                "element_class": "link",
                "element_text": "Click me",
                "value": "",
                "key": "",
                "x": 0,
                "y": 0,
                "session_id": "http-test-session",
            }]
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:17834/dom-events",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("count"), 1)


class TestGenerateFromDomEvents(unittest.TestCase):
    def test_empty_session(self):
        import playwright_gen
        script = playwright_gen.generate_from_dom_events("nonexistent-session-xyz")
        self.assertIn("Steps: 0", script)
        self.assertIn("No DOM events captured", script)

    def test_two_click_events(self):
        import db
        import playwright_gen
        events = [
            {
                "type": "click",
                "url": "https://example.com/page",
                "timestamp": "2024-01-01T00:00:01Z",
                "selector": "#submit",
                "element_tag": "button",
                "element_id": "submit",
                "element_class": "",
                "element_text": "Submit",
                "value": "",
                "key": "",
                "x": 0,
                "y": 0,
                "session_id": "gen-test-session",
            },
            {
                "type": "click",
                "url": "https://example.com/page",
                "timestamp": "2024-01-01T00:00:02Z",
                "selector": ".cancel",
                "element_tag": "a",
                "element_id": "",
                "element_class": "cancel",
                "element_text": "Cancel",
                "value": "",
                "key": "",
                "x": 0,
                "y": 0,
                "session_id": "gen-test-session",
            },
        ]
        db.insert_dom_events(events)
        script = playwright_gen.generate_from_dom_events("gen-test-session")
        self.assertIn("Steps: 2", script)
        self.assertIn('page.locator("#submit").click()', script)
        self.assertIn('page.locator(".cancel").click()', script)
        self.assertIn('page.goto("https://example.com/page")', script)


if __name__ == "__main__":
    unittest.main()
