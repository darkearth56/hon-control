# hOn control

Stop, pause and resume services for Haier, Hoover and Candy washers and washer-dryers on the [gvigroux/hon](https://github.com/gvigroux/hon) Home Assistant integration.

gvigroux/hon can start programs, but it has no working way to stop or pause one. Its `hon.turn_off` service sends a power-off request instead of a stop. This small companion integration sends the same `stopProgram`, `pauseProgram` and `resumeProgram` commands the hOn app uses.

It is kept separate from gvigroux/hon so that updating that integration never overwrites these services. It doesn't log in on its own: it reuses the hon integration's connection and the command list it has already loaded for each appliance.

## Tested on

- Hoover H-Wash & Dry 400 (BH4S696M6DB9-80), integrated, Wi-Fi enabled, 9 kg washer-dryer

Pause, resume and stop were each accepted by the hOn cloud and reached the machine in about a minute. Other Haier, Hoover and Candy washers should work if `list_commands` shows the `stopProgram`, `pauseProgram` and `resumeProgram` commands, but they haven't been tested.

## Requirements

- [gvigroux/hon](https://github.com/gvigroux/hon) installed and working
- Remote control enabled on the machine

## Install

### HACS

1. HACS → three-dot menu → **Custom repositories**
2. Add `https://github.com/darkearth56/hon-control` with type **Integration**
3. Install **hOn control** and restart Home Assistant
4. Settings → Devices and services → **Add integration** → **hOn control**. There are no settings.

### Manual

1. Copy `custom_components/hon_control` into your `config/custom_components` folder
2. Restart Home Assistant
3. Settings → Devices and services → **Add integration** → **hOn control**

## Services

Every service targets an hOn device.

| Service | Sends | Notes |
| --- | --- | --- |
| `hon_control.stop_program` | `stopProgram` | Ends the running cycle |
| `hon_control.pause_program` | `pauseProgram` | Pauses the running cycle |
| `hon_control.resume_program` | `resumeProgram` | Resumes a paused cycle |
| `hon_control.list_commands` | nothing | Returns the commands your appliance supports and the values each one sends. Use it to check what your model accepts |

Each command is sent with the parameter values the hOn cloud defines for it. On the tested washer-dryer those are fixed: `stopProgram` sends `onOffStatus: 0`, `pauseProgram` sends `pause: 1`, and `resumeProgram` sends `pause: 0, restartGN: 1`.

If the hOn cloud rejects a command, or the appliance doesn't have it, the service raises an error you can see, so automations can react with `continue_on_error` or a check afterwards.

### Examples

```yaml
action: hon_control.pause_program
target:
  device_id: YOUR_HON_DEVICE_ID
```

```yaml
action: hon_control.list_commands
target:
  device_id: YOUR_HON_DEVICE_ID
response_variable: commands
```

The machine takes about a minute to report a change back to Home Assistant, so allow for that before checking its state.

## Dashboard card

[hon-wash-dryer-card](https://github.com/darkearth56/hon-wash-dryer-card) shows Pause/Resume and Stop buttons automatically when this integration is installed.

## Credits

- The idea comes from [mmalolepszy/hon-revived](https://github.com/mmalolepszy/hon-revived) and its fork [galvani/hon](https://github.com/galvani/hon), whose washer switches send `stopProgram`/`startProgram` and `pauseProgram`/`resumeProgram`. Both continue Andre Basche's original [Andre0512/hon](https://github.com/Andre0512/hon) integration and pyhOn library.
- [gvigroux/hon](https://github.com/gvigroux/hon) does all the work of logging in to the hOn cloud and loading each appliance's commands. This integration only sends commands through it. gvigroux/hon already had a `stop_command()` for climate and water heater devices, which showed the command was available to washers too.
- No code is copied from these projects.

## Licence

MIT
