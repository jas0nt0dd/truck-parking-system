import asyncio

from app.services import messaging


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    async def aread(self):
        return b'{"status": "ok"}'

    def json(self):
        return {"status": "ok"}


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        self.requests.append({"url": url, "json": json, "headers": headers})
        return FakeResponse()


def test_send_builds_entry_components_in_placeholder_order(monkeypatch):
    captured_clients = []

    def factory(*args, **kwargs):
        client = FakeAsyncClient(*args, **kwargs)
        captured_clients.append(client)
        return client

    monkeypatch.setattr(messaging.httpx, "AsyncClient", factory)

    config = messaging.MSG91Config(
        authkey="auth-key",
        sender_id="sender-id",
        whatsapp_number="+15551234567",
        entry_template="entry-template",
        exit_template="exit-template",
        enabled=True,
        parking_name="Smart Truck Parking",
    )
    provider = messaging.MSG91WhatsAppProvider(config)

    asyncio.run(provider._send("entry-template", "+919876543210", ("TN01AB1234", "Smart Truck Parking", "09/07/2026 03:30 PM", "9876543210")))

    request = captured_clients[0].requests[0]
    components = request["json"]["payload"]["template"]["to_and_components"][0]["components"]
    assert list(components.keys()) == ["body_1", "body_2", "body_3", "body_4"]
    assert [component["value"] for component in components.values()] == [
        "TN01AB1234",
        "Smart Truck Parking",
        "09/07/2026 03:30 PM",
        "9876543210",
    ]


def test_send_builds_exit_components_in_placeholder_order(monkeypatch):
    captured_clients = []

    def factory(*args, **kwargs):
        client = FakeAsyncClient(*args, **kwargs)
        captured_clients.append(client)
        return client

    monkeypatch.setattr(messaging.httpx, "AsyncClient", factory)

    config = messaging.MSG91Config(
        authkey="auth-key",
        sender_id="sender-id",
        whatsapp_number="+15551234567",
        entry_template="entry-template",
        exit_template="exit-template",
        enabled=True,
        parking_name="Smart Truck Parking",
    )
    provider = messaging.MSG91WhatsAppProvider(config)

    asyncio.run(
        provider._send(
            "exit-template",
            "+919876543210",
            (
                "TN01AB1234",
                "Smart Truck Parking",
                "09/07/2026 03:30 PM",
                "09/07/2026 07:45 PM",
                "4 hours 15 minutes",
                "150",
                "cash",
            ),
        )
    )

    request = captured_clients[0].requests[0]
    components = request["json"]["payload"]["template"]["to_and_components"][0]["components"]
    assert list(components.keys()) == ["body_1", "body_2", "body_3", "body_4", "body_5", "body_6", "body_7"]
    assert [component["value"] for component in components.values()] == [
        "TN01AB1234",
        "Smart Truck Parking",
        "09/07/2026 03:30 PM",
        "09/07/2026 07:45 PM",
        "4 hours 15 minutes",
        "150",
        "cash",
    ]


def test_send_uses_msg91_control_host_and_accept_header(monkeypatch):
    captured_clients = []

    def factory(*args, **kwargs):
        client = FakeAsyncClient(*args, **kwargs)
        captured_clients.append(client)
        return client

    monkeypatch.setattr(messaging.httpx, "AsyncClient", factory)
    monkeypatch.setattr(messaging.settings, "MSG91_BASE_URL", "https://control.msg91.com/api/v5")

    config = messaging.MSG91Config(
        authkey="auth-key",
        sender_id="sender-id",
        whatsapp_number="+15551234567",
        entry_template="entry-template",
        exit_template="exit-template",
        enabled=True,
        parking_name="Smart Truck Parking",
    )
    provider = messaging.MSG91WhatsAppProvider(config)

    asyncio.run(provider._send("entry-template", "+919876543210", ("TN01AB1234",)))

    request = captured_clients[0].requests[0]
    assert request["url"].startswith("https://control.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/")
    assert request["headers"]["accept"] == "application/json"


def test_send_normalizes_phone_numbers(monkeypatch):
    captured_clients = []

    def factory(*args, **kwargs):
        client = FakeAsyncClient(*args, **kwargs)
        captured_clients.append(client)
        return client

    monkeypatch.setattr(messaging.httpx, "AsyncClient", factory)

    config = messaging.MSG91Config(
        authkey="auth-key",
        sender_id="sender-id",
        whatsapp_number="917200775876",
        entry_template="entry-template",
        exit_template="exit-template",
        enabled=True,
        parking_name="Smart Truck Parking",
    )
    provider = messaging.MSG91WhatsAppProvider(config)

    asyncio.run(provider._send("entry-template", "9876543210", ("TN01AB1234",)))

    request = captured_clients[0].requests[0]
    assert request["json"]["integrated_number"] == "+917200775876"
    assert request["json"]["payload"]["template"]["to_and_components"][0]["to"][0] == "+919876543210"
