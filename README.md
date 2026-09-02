## What is this library? 

This is a basic Python library for interfacing with certain late-2000s era Yamaha receivers via the 'Web Control Interface'.

Current tested models are:

- RX-V3900

Other models theoretically supported by this library include:

- RX-Z7
- DSP-Z7

Not a long list, but I don't have any other hardware to test with.  If you have a Yamaha receiver from around this era that has a Web Control Interface, please let me know and we can do some testing!

## Installing

We are now on TestPyPi!  While I still sort out the kinks, this library is only available on the PyPi testing server (as opposed to the main server).

To install, you just need to direct pip to the testing server, as follows:

```
pip install -i https://test.pypi.org/simple/ legacy-yamaha-receiver-control
```

Then just run:

```
yamaha-receiver
```

Or pass in specific commands, as set out further below.

## What can you do with this?

At present, this library can perform all* of the functions you can do directly through the Web Control Interface, including:

- Turning the amplifier on and off
- Turning individual zones on and off
- Adjusting the volume of each zone, including muting each zone
- Selecting inputs for each zone
- Selecting an audio program for the main zone (other zones do not have audio programs)

What you cannot do with this library (or the Web Control Interface) is adjust any of the settings or input allocations for the receiver.  They must be done through the on-screen GUI.

\* The only functions I have not implemented are those that I think no person would reasonably expect to use, so I have left these for a later release.  The main ones I have identified are:

- Using the radio - you can select a radio station directly through the Web Control Interface, but the protocol behind it is a bit finnicky.  It can be done, I just didn't consider it a priority for a first release. 
- Using the other radio-like functions (such as Sirius and Rhapsody) - I don't have the hardware to test this (in the case of Sirius), and I don't live in the US (which is a barrier for Rhapsody), and so I can't analyse the setup process.  I also really don't know if anyone is still using this...
- Using the iPod dock - I do actually have one of these, and an iPod to test it with, but I figured that the audience for this would be ... limited, and hence not a priority for a first release.
- Using the bluetooth - Same story as Sirius.  This required a hardware addon which I don't have, and so I can't test how the setup process works.
- Using the sleep function - this seems to be some sort of timer function whree you can set the amplifier to turn off after a certain fixed interval (e.g. 30 minutes, 60 minutes, etc.).  I ... honestly can't imagine a situation where this would be useful.

So we have a lot of core functionality, but with room to move!

## Command-line interface

Running `yamaha-receiver` without arguments prompts for the receiver IP address and then accepts commands until `quit` is entered. You can also provide the IP address immediately with `yamaha-receiver 192.168.1.XX`; this starts interactive mode without prompting for the address. Interactive mode refreshes all zone statuses immediately and about every 10 seconds while waiting for commands. Commands can also be supplied directly:

```text
yamaha-receiver 192.168.1.XX status
yamaha-receiver 192.168.1.XX power main on
yamaha-receiver 192.168.1.XX input main CD
yamaha-receiver 192.168.1.XX volume main -400
yamaha-receiver 192.168.1.XX mute main on
yamaha-receiver 192.168.1.XX audio main STRAIGHT
```

Available zones are `main`, `zone2`, and `zone3`. Input and audio program arguments use the enum names in `enums.py`; for example, `CD` and `TUNER` (for inputs); and `STEREO_TWOCH` and `ADVENTURE` (for audio programs). 

Use `yamaha-receiver --help` for the command list before connecting, or enter `help` at the interactive prompt.

## How does this library work?

Yamaha receivers from this era have a web interface that you can access by connecting the receiver to your network via an ethernet cable and just browsing to the IP address.  It is a fairly charming (if rudimentary) interface, with some basic buttons.

The interface itself is a basic HTML page with Javascript, but all of the communication with the receiver is done with HTTP post requests.  The Javascript polls each of the zones for the receiver every second or so to check for the status, and then also delivers any user commands through the same means.

After spending quite a bit of time in the network analyser tab, it was fairly trivial (if time consuming) to determine the structure of the post requests and reverse engineer them.  The requests themselves use an XML structure, so it is just a matter of ingesting the incoming XML information and then reconstructing the XML structure that the receiver expects to see. 

This library is a basic asynchronous library that uses the Python 'aiohttp' library to issue post requests to the receiver. It is anticipated that this will be used with a Home Assistant integration that then uses this library for communication with the receiver, but I also wanted to make it standalone in case that was useful.

## Why did you do this?

I had an old Yamaha receiver from around 2009 that I wanted to use to connect to some speakers and handle some analog inputs.  It being 202X, I wanted to automate some of this handling through Home Assistant, but none of the existing integrations target this era of Yamaha receivers. Later recievers use 'YNCA', which has much better features and documentation (see for example [this Home Assistant extension](https://community.home-assistant.io/t/custom-component-yamaha-ynca/452494)).  For those receivers that had some web control, but pre-dated YNCA, there were no existing options available.

This is not a unique experience for this receiver.  Much of the equipment from this era has advanced functions that are locked behind dated platforms, apps that no longer exist, or long-forgotten protocols.  This is a basic library that reinstates that functionality, helping to bringing this (very capable) hardware into the modern era. After all, this receiver can do 1080p, 7.1 surround sound, 3 zone audio and a huge variety of analog and digital inputs - it's no slouch!

I am grateful to the tireless Yamaha engineers that designed the Web Control Interface, and who were perhaps disappointed to see it replaced with flashier services very shortly after this model's release. All the hard work was done by them, I just revealed what was already there.

Before someone asks, these receivers do have RS-232 ports, however I believe all this capability has all been hard-disabled in firmware. I saw some rumours online that earlier versions of the firmware had left the RS-232 port active, but I couldn't determine whether this was correct.  Even if the RS-232 port could be activated, it seems to use some sort of bespoke protocol that would also have to be reverse engineered. I am game, however, if someone can find a way!

## Licence

There is a separate licence file, so please read that for the full details.  I would hope that this library is useful for people (or perhaps at least one other person), and you can use it however you wish, provided that you please attribute the original library and don't charge people to use it.