# Voice acceptance tests

The automated name-taking test loads the application with `app.load()` and
uses its production clients, gateways, Restate workflow/actions, and Postgres
repository. Three simulated people join real LiveKit rooms and reply with
model-generated speech. No SIP trunk or telephone number is needed.

The test checks each saved name through `get_call` and checks the final agent
transcription received by the person in the room. It does not independently
transcribe the agent's audio. The simulated person is instructed to provide
their name only when asked.

Start the local Postgres and Restate services described in `scripts/verify`.
Set `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` for a test project,
then run from the repository root:

```sh
VOICE_EVALS=1 LIVEKIT_AGENT_NAME=caller-acceptance scripts/verify voice
```

Use an agent name not served by another worker. The verification script starts
the production Restate HTTP host and registers it with Restate, and with
`VOICE_EVALS=1` it also starts the production LiveKit agent server
(`srv.livekit.agent_server`) under that agent name. The tests are clients of
both: each one places a call through the loaded app while a simulated person
(`simulated/person.py`, a directory the analyzer does not govern) watches
LiveKit for the room the agent was dispatched into, joins it as `person`, and
answers either when asked or over the question.

Defaults are Postgres at `localhost:5434` and Restate ingress/admin at
`localhost:28080`/`localhost:29070`. Override them with `CALLS_STORAGE`,
`RESTATE_INGRESS`, and `RESTATE_ADMIN`. This test uses paid LiveKit/model APIs
and is skipped unless `VOICE_EVALS=1`.
