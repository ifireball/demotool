IDEAS, what was done, where is this going?
==========================================

POC log - checking vncdotool
----------------------------

A Fedora 42 VM was setup manaully using virt-manager. Settings were changed
manually to use VNC instead of Spice. From that point on it was available at:

```bash
vnc://localhost:5600
```

The VM can be controlled from `vncdotool`. Here are some examples:

Unlocking the lock screen (note the password in the clear here...):

```bash
vncdotool -s 127.0.0.1::5900 type demokudasaidomo key enter
```

Starting the calculator from the activities menu, waiting 5 seconds, then
closing it with the keyboard:

```bash
vncdotool -s 127.0.0.1::5900  move 10 10 click 1 pause 3 \
    type calculator pause 3 \
    key enter pause 5 \
    keydown alt key f4 keyup alt
```

We can use VLC the to record the VNC stream to a video file. The command
records the video while also showing it on screen in the VLC player window:

```bash
vlc -vvv vnc://localhost:5900 \
    --sout="#duplicate{dst=display,dst='transcode{vcodec=h264,acodec=mp3,ab=128}:std{access=file,mux=mp4,dst=$HOME/Videos/vm-record1.mp4}'}" \
    --sout-keep
```

Note: this does not record the mouse pointer. The VLC `--screen-mouse-image`
option might help here, you set it to an image of the mouse pointer like:

```bash
/usr/share/icons/Adwaita/cursors/default
```

(I did not try this yet, need a longer vncdotool program to bounce the mouse
around on the screen)

To stop the recording we must click "stop" on the UI, hitting Ctrl+C on the
running CLI causes it not to save the video file. According to Gemini we can
solve this by using `-I rc` to enable a remote control interface for VLC on
port 4212. We can then send commands to it with something like `nc`, for
example:

```bash
echo "quit" | nc localhost 4212
```

Node: can add `--rc-quiet` to make VLC less noisy on its STDOUT (Would
probably also want to not pass `-vvv` when doing this).

This gives us basic tools to start a recording, do something in the VM then
stop.

Where do I go from here
-----------------------

Looked into various ideas of making this ito a fully-fledged "VNCd with
automation and recording" desktop program. Putting ths aside for now. I want
to make demos, not just tools for making demos!

Do we need to add an LLM into the mix? Maybe not - xdotool-ish language might
be enough. But we want a little bit more automation:

Idea 1: Shell/Python script to start recording then run vncdotool with a given
file as input, and stop recording when its done. This could be set as a "run"
command for the file in VScode. But we want more then this - smooth mouse
motion without writing huge files, finer control over recroding like preparing
the VM without recording or recording different sections into different files.

Idea 2: Create an enhanced version of the vncdotool language with moution
commands, recording commands, VM setup commands. But who wants to write a
parser, VScode won't highlight it, LLMs won't generate it

Idea 3: Use Python as a DSL. Problem: It'll confuse the IDEs and LLMs.

Idea 4: Just write plain Python, use vncdotool as a library, along with
(possibly) python-vlc, and the python bindings for libvirt.

So wer'e going with idea 4.

Using plain Python for demo generation
--------------------------------------

For each demo we want to make, we will write a new Python script to record it.
Where ths script will essentially use the vncdotool API.

To reduce the amount of boilerplate in the scripts, we will need modules to do
the following for us:

1. Setup the VM (or at least check its there and figure out the VNC port)
2. Snapshot/restore the VM
3. Start/Stop recording
4. Perform smooth mouse motion between points.
5. Type slowly
6. Skip sections we don't need to do - for e.g. don't create the VM if it was
   already created.

Example for how a demo generation script would look like:

```python
import demotool

# Designates the `demo-videos/my-cool-demo` directory where all output 
# vidoes would be stored. The directory is named here but would only get
# created once we actually start recording a video, or not at all.
# The `demo-videos` directory should probably be in `.gitignore`
with demotool.startdemo("my-cool-demo") as demo:
    # Start a demo VM. The VM name would be based on the demo name. The
    # image is based on the virt-builder template with the given name, 
    # with the @workstation-product-environment package installed.
    # images would be stored in the relevant XDG cache directory so that
    # the image for a given distro version is only created once.
    # The VM itself would use a COW layer on top of the original image.
    with demo.vm("fedora-42") as vm:
        # Ensure we are logged-in to a desktop session for a demo user we
        # created during image insallation
        vm.unlock()
        # Start recording video to `demo-videos/my-cool-demo/calc.mp4
        with vm.record("calc"):
            # the vm object basically exposes an augmented vncdotool API

            # Move the mouse pointer to the center of the screen
            vm.mouseMoveCenter()
            # Animate moving the mouse to 10,10
            vm.mouseDrag(10, 10, step=10)
            vm.mousePress(1)
            vm.pause(3)
            # Animate typing
            vm.type("calculator")
            vm.pause(3)
            vm.keyPress("enter")
            vm.pasue(5)
            # Type key combinations - press down all keys then release 
            # in reverse order
            vm.keyCombo("alt", "f4")
```
