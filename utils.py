# stuff for AutoEdit to use

import re
import numpy as np

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

def MergeMissingDictIntoFinalDict(finalDict, missingDict):
    # helper function for the missing merge stuff - see the comments at this point in the main loop for full logic here
    for m in missingDict:
        mEndTime = m["end"]
        # find the finalDict entry that has a start to match this end (all the times should be unique, so there should be only 1 match (should be, lolololol)
        foundIt = -1 # -1 when it wasn't found, otherwise will hold the index our info was found at
        for i, f in enumerate(finalDict):
            if f["start"] == mEndTime:
                # get the estimated start time for our missing sgement from the next one
                m["start"] = finalDict[i+1]["end"]
                foundIt = i+1 # store the index we need to insert the new value at
                break
        if(foundIt>-1): # insert our completed missing entry into the finalDict
            finalDict.insert(foundIt,m)

    return finalDict

def PrintScriptEstimationFromDict(theDict):
    # just puts all the words from our 'dict' structure (actually a list of dicts) into the print output
    # we need to work with a copy of the dict, since we're about to reverse it, and it automatically acts like a ref arguement
        myDict = theDict.copy()
        myDict.reverse() # generally teh dict is backwards throughout processing
        scriptEstimation = ""
        for x in myDict:
            scriptEstimation += x["word"] + " "
        print(f"Script estimation:\n{scriptEstimation}")


def PrintActualScript(wordList):
    # shows what the script should be accord to teh wordList (list of strings)
    script = ""
    for x in wordList:
        script += x + " "

    print(f"Actual script:\n{script}")

def ShaveFinalDictToConfirmedMatches(finalDict, wordList):
    # shall return the finalDict entries that create a good match with teh script up to a given point, and an index related to that point - see comments in main loop for full logic

    newStartIndex = -1 # this default valueu will halt the main loop if we find the match with the script is 'good enough' the whole way. what the words 'good enough' mean are
                        # the main thing we need to decide in this function

    # note, the dict is backwards, bu tthe worldList is forwards, so we need to use...
    script = wordList.copy()
    script.reverse()

    # ERROR RESOLUTION VARIABLE
    # this is a key concept. we need to decide how many errors need to be a row for a suitable break in the coparison to have been found. all i know is that small numbers of errors
    # resulting from weird names, potentially with many words, is entirely possible, so this number needs to be long enough to let such things through, to avoid having way too many
    # passes. the main goal is detecting errors that mess everything up, like searching an 'and' and landing on one way ahead in the script, which then will oblitarate the main loop.
    errorRes = 3

    # HOW TO DETERMINE WHERE THE ERROR STARTED
    # this is key too, because the errors WON'T necessarily begin right after the troublemaker word. because small words, like 'the' and such will likely be found after a large,
    # intended 'read-head' skip forward cuased by transscript issues, and hence show up looking fine to function. but it's actually the wrong 'the'. thsi si very hard to detect
    # because the transcription is allowed to contain any number of errornous of repeated 'the's, so jumping ahead an arbitrary distance to find one isn't disallowed in in principal

    # ------------------------------------------------------------
    # MAIN COMPARISON LOOP
    errorCount = 0
    i = 0
    while i < len(finalDict) and i < len(script):
        a = finalDict[i]["word"].strip()
        b = script[i].strip()

        # is it a match?
        if(a == b):
            errorCount = 0
        else:
            errorCount = errorCount +1

        # enough errors to call it a break in the script?
        if errorCount >= errorRes:
            newStartIndex = i - errorCount # note its -errorCount as we want to go back to when the errors started - in a momnet thish will be moved on 1 more by the processing to come, see below
            break

        i = i+1 # end of main loop

    # ----------------------------------------------------------
    # AMMENDMENT
    # now, if start index isn't -1, we need to add a word to the final dict from the script, and then start the next pass from the next word
    if newStartIndex > -1:
        # *** coming soon

        # ESTIMATE THE FINALDICT ENTRY FOR THE TROUBLEMAKER WORD - SOMEHOW!***


        # GET RID OF THE BIT THAT WILL BE REGENERATED IN NEXT PASS
        # next pass starts from next index
        newStartIndex = newStartIndex -1

        # slice off the part we don't want anymore
        del finalDict[newStartIndex:] # python is good for this kinda thing, even ifthis syntax looks meaningless

        # finally we note that because the word list is ordered forwards but iterated bacjwards, the index is actually...
        newStartIndex = len(wordList)-1-newStartIndex

    return finalDict, newStartIndex



def GetLevensteinDistance(word1, word2): # taken from somewhere or other
    m, n = len(word1), len(word2)
    
    matrix = np.zeros((m+1, n+1), dtype=int)
    
    matrix[:, 0] = np.arange(m+1)
    matrix[0, :] = np.arange(n+1)
    
    for i in range(1, m+1):
        for j in range(1, n+1):
            if word1[i-1] == word2[j-1]:
                substitution_cost = 0
            else:
                substitution_cost = 1

            matrix[i, j] = min(
                matrix[i-1, j] + 1,                # deletion
                matrix[i, j-1] + 1,                # insertion
                matrix[i-1, j-1] + substitution_cost    # substitution
            )
    
    similarity = 1 - matrix[m, n] / max(m, n)
    similarity_percentage = similarity * 100
    
    return similarity_percentage


