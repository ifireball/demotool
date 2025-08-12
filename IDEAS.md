IDEAS, what was done, where is this going?
==========================================

POC log - checking vncdotool
----------------------------

A Fedora 42 VM was setup manaully using virt-manager. Settings were changed
manually to use VNC instead of Spice. From that point on it was available at:

    vnc://localhost:5600

The VM can be controlled from `vncdotool`. Here are some examples:

Unlocking the lock screen (note the password in the clear here...):

    vncdotool -s 127.0.0.1::5900 type demokudasaidomo key enter

Starting the calculator from the activities menu, waiting 5 seconds, then
closing it with the keyboard:

    vncdotool -s 127.0.0.1::5900  move 10 10 click 1 pause 3 \
        type calculator pause 3 \
        key enter pause 5 \
        keydown alt key f4 keyup alt

We can use VLC the to record the VNC stream to a video file. The command
records the video while also showing it on screen in the VLC player window:

    vlc -vvv vnc://localhost:5900 \
        --sout="#duplicate{dst=display,dst='transcode{vcodec=h264,acodec=mp3,ab=128}:std{access=file,mux=mp4,dst=$HOME/Videos/vm-record1.mp4}'}" \
        --sout-keep

Note: this does not record the mouse pointer. The VLC `--screen-mouse-image`
option might help here, you set it to an image of the mouse pointer like:

    /usr/share/icons/Adwaita/cursors/default

(I did not try this yet, need a longer vncdotool program to bounce the mouse
around on the screen)

To stop the recording we must click "stop" on the UI, hitting Ctrl+C on the
running CLI causes it not to save the video file. According to Gemini we can
solve this by using `-I rc` to enable a remote control interface for VLC on
port 4212. We can then send commands to it with something like `nc`, for
example:

    echo "quit" | nc localhost 4212

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
