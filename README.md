# Auto-VO-Editor
A python application (currently .py script and CLI only) that looks an Audacity OpenVINO Whisper.cpp transcript of an audio file, alongside the script the performer used to create that audio file, and then slices the transcript file down to only the correct takes, such that it represents only the timestamps of the correct parts of the file.

This can be used in Audacity to indicate where the editor needs to cut the file down to create the finished file, with potentially dramatically reduced need to listen to the whole session recording.

Important note: outsourcing editorial decision making to a program with a fuzzy AI transcription routine at its core if a very dumb idea. Proceed with caution and always backup raw recordings before editing with any shortcut methods such as this.

## Outline

This Python script will take transcript outputs from Audacity's OpenVINO implementation of whisper.cpp, and compare them to the true script.

Because the transcription process is far from perfect, myriad measures and checks are required to have any hope of programatically identifying all the correct segments of the transcript needed to build the true script, and their associated timestamps.

When the timestamps are ready, they can, IN PRINCIPAL, be used to auto-edit the recording that transcript was based on, instantly cutting it down to only the parts needed to fulfil the true script, skipping a major part of day-to-day audio editing for simple narrations, podcasts, lesson delivery... anything that has a transcript-friendly audio file and needs to exactly follow a script. However, for now, this program will stop short of that, and leave the actual 
'auto-edit' part to the user, following the questionable guidance of the timestamps in the transcript this program creates.

## Documentation Coming Soon...

The workflow for the use of this program will be:
1) Create the raw recording by performing the script.
2) Use the Open VINO Whisper transcription process to create the transcribed label track (more on this coming soon...)
3) Export the label file in its default .txt format.
4) Create a .txt copy of the script that doesn't contain ANY non-voiced elements. e.g. delete titles or directions.
5) Run this program on the transcript and script .txt. Generally do what the program says. (Currently it's only CLI and the AutoEdit.py script must be hand-edited to select the relevant filepaths.) (more on this coming soon.)
6) The program outputs a new transcript .txt. Import this into your Audacity project as a new label track.
7) It should now only label the 'correct' parts of the recording, so you can edit it down to these. Note Audacity has built in label-edit features like the ability to copy all the labelled parts, which may be handy.
8) When you realise you accidentaly mis-edited something by relying on the labelling to be more correct than it is, remember that OffyD warned you this would happen, and hold no hate in your heart.

## Update History

### 0.5
The big Super Guess Mode update, which allows the script to produce a much more automated and potentially error prone final output at rapid speed. 
Intregrates a new 'Troublemaker Hunter' automated error checking system that is much better at dealing with the assorted problems raised by transcription errors.
So the script now has 2 main modes: automatic (versions 0.1 and 0.5) and user-input based (0.3 and 0.4). User input can allow for a perfect final transcript, but its
quite slow to achieve, defeating the purpose of the program. Super Guess Mode will be the new default approach, seeking to achieve a 'good enough' result in a fraction of the time.

### 0.4
Fuzzy matching is now available, reducing the amount of user input needed when transcripts are inaccurate (i.e. very often). This only effects words of 5 characters or more, and requires 80%+ plus similarlity (Levenstein similarity - based on the amount of changes needed to get to the exact match).

### 0.3
Added the ability for the program to ask the user to confirm the correct transcript entries for cases where a solid automatic match cannot be established. 
A basic CLI has been added to facilitate this, with handy features to make finding the correct entry quicker and easier.
User input triggers some automatic error checking that can use the user input to root out problems the program missed, asking for further user input to clarify suspected errors. This allows quite robust transcript comprehension and error handling, however it does require a lot of user input i.e. what we don't want this program for, so future versions will try to get more clever and require the user less.

### 0.1
Improved transcript to script alignment process, and added the ability to output a new transcript with only the 'correct' parts so that it can be imported to Audacity as a manual editing aid - this is the 'safe' approach to this script's intended functionality, with no handling of the actual audio file by the script.

### 0.0.1
Basic transcription to script alignment process, with ability to handle errors, do multiple passes, and assess accuracy of results.
