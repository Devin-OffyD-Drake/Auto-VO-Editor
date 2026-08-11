# Auto-VO-Editor
A python application that trims an audio file so that it fits a given script as closely as possible.

## Outline

This Python script will take transcript outputs from Audacity's OpenVINO implementation of whisper.cpp, and compare them to the true script.

Because the transcription process is far from perfect, myriad measures and checks are required to have any hope of programatically identifying all the correct segments of the transcript needed to build the true script, and their associated timestamps.

When the timestamps are ready, they can be used to auto-edit the recording that transcript was based on, instantly cutting it down to only the parts needed to fulfil the true script, skipping a major part of day-to-day audio editing for simple narrations, podcasts, lesson delivery... anything that has a transcript-friendly audio file and needs to exactly follow a script.

## Documentation Coming Soon...

## Update History

### 0.1
Improved transcript to script alignment process, and added the ability to output a new transcript with only the 'correct' parts so that it can be imported to Audacity as a manual editing aid - this is the 'safe' approach to this script's intended functionality, with no handling of the actual audio file by the script.

### 0.0.1
Basic transcription to script alignment process, with ability to handle errors, do multiple passes, and assess accuracy of results.
