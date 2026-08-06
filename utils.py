# stuff for AutoEdit to use

import re

# first we need a function that will take our transcript file, and turn it into a structure with three values per entry: start time, end time, and the word/phoenem.
def LoadTranscript(path):
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t") # split on \t means tab. can try no arg to split on whitespace, which may also fit the way the file is outfrom from OpenVINO.
                
                if len(parts) != 3: # check for the line being invalid - should never happen since the output is standardised
                    continue
                
                start, end, word = parts # define 3 variables from the 3 things we should have got from our split. we expect number, number, string

                word = re.sub(r"[^\w\s]", "", word).strip().lower() # gonna work all in lower case for this, and no punctuation (note this may leave word as empty string) *** may want to ignore the empty rows depending on how the final recording edits end up sounding with these left in
                
                entries.append({
                    "start": float(start),
                    "end": float(end),
                    "word": word
                }) # we're making a list of dictionaries, with 3 keys, which lets us call them back with something like entries[100]["start"] tp get the start numebr for row 100.
    except:
        print("Failed to load transcript.")
        
    return entries


# we need a function that will import our intended script file, and then divde it into a big list of strings, word by word
def LoadExpectedScript(path):
    try:
        text = open(path, "r", encoding="utf-8").read()
        text = text.lower()

        # we can't let this program match punctuation, since there is no way whisper will 100% notice what is a comma/fullstop in the audio and transcribe accordingly.
        text = re.sub(r"[^\w\s]", "", text)
        
        words = text.split()
        return words
    except:
        print("Failed to load expected script")
        return ""
