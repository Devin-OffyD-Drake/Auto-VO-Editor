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

def ShaveFinalDictToConfirmedMatches(finalDict, wordList, bestFinalDict):
    # shall return the finalDict entries that create a good match with teh script up to a given point, and an index related to that point - see comments in main loop for full logic

    newStartIndex = -1 # this default valueu will halt the main loop if we find the match with the script is 'good enough' the whole way. what the words 'good enough' mean are
                        # the main thing we need to decide in this function

    # do time check
    doTimeCheck = False # EXPERIMENTAL FEATURE THAT BERAKS EVERYTHING WHIEL TRYING TO FIX IT

    newIndexSet = False # matters right at the end

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
    # MAIN WORD COMPARISON LOOP
    errorCount = 0
    i = 0
    while i < len(finalDict) and i < len(script):

        # -----------------------
        # WORD MATCH CHECK
        a = finalDict[i]["word"].strip()
        b = script[i].strip()

        # is it a match?
        if(a == b):
            errorCount = 0
        else:
            errorCount = errorCount +1

        # enough errors to call it a break in the script?
        if errorCount >= errorRes:
            newStartIndex = i - errorCount # note its -errorCount as we want to go back to when the errors started - in a momnet this will be moved on 1 more by the processing to come, see below
            newIndexSet = True
            break
        
        i = i+1 # end of main loop
        # -------------------------

    # ---------------------------------------------------------
    # TIME JUMP CHECK LOOP
    if doTimeCheck == True:
        # this check runs not on the fianlDict, but on the previous bestFinalDict + finalDict combo aka what the output of this pass would ultimately be.
        # we are looking for cases where something appears out of time sequence, mainly meaning a word thats timestamps are studdenly further long, then the next work jump sback to a previous
        # point. this can happen when passes are joined together and a previous pass contains a troulemaker word that was let in due to a false positive in the transcript of perhaps as a
        # result of manual meddling, like the missingDict integration step. so, we will make a temp complete dict to look through here, and be careful about what index we need to use
        # as a result.
        tjStartIndex = 0 # i wish i could yse null to show us that it was never changed, as all values are theoretically valid. i will use a bool instead
        tjStartIndexSet = False
        tempDict = bestFinalDict.copy()
        tempDictLen = len(tempDict) # need to store this for future index stuff
        tempDict.extend(finalDict) # now its an estimate of the finished pass output
        i = 0
        iNext = 1
        
        while i < len(tempDict) and iNext<len(tempDict):

            if tempDict[i]["end"] < tempDict[iNext]["start"]: # if the next one has a higher time, it was found earlier in the transcript loop (goes backwards yeah), which should never happen
                tjStartIndex = i - tempDictLen # we substract the length of the orignal dict, and so if startindex<0 we know the problem was actually in the PREVIOUS pass.
                tjStartIndexSet = True
                word = tempDict[i]["word"]
                print(f"Time Jump Check has triggered. Word: {word}")
                break
                
            i = i + 1
            iNext = i +1

        if tjStartIndexSet == True: # if false, this check found nothing, and we will do nothing, simples
            if(tjStartIndex < 0):
                # the newStartIndex will need to be BEFORE teh start of the current pass, which requires us to totally discard our finalDict and shave the bestFinalDict down to teh
                # trouble point. since we have the refs to them, we can go ahead, and then the main loop calling this should carry on merrily
                newStartIndex = i # LOGIC SHIFT occuring here where newStartIndex starts to refer ONLY the index of the word list, not final dict. final dict will be discarded
                newIndexSet = True
                del bestFinalDict[newStartIndex:] # slices this down to the troublemaker
                finalDict.clear()
                print(f"bestFinalDict has been stripped back to index {newStartIndex}.")

            else: # the problem was in the current pass. this might actually be impossibe to trigger because the current pass is always in a chronological order. but let's handle it anyway.
                if(tjStartIndex < newStartIndex):
                    newStartIndex = tjStartIndex # we allow this to overwruite the previous check's troublemaker point, if its earlier
                    newIndexSet = True

    # ----------------------------------------------------------
    # AMMENDMENT
    # now, if start index isn't -1, we ideally need to manually indentify the troublemaker and handle it specially, and then start the next pass from the next word
    # *** however, since no complete way to know the troublemaker has been developed yet, we can't do much but skip it and try to get the rest right for the time being

    if newStartIndex > -1 and len(finalDict)>0: # second check because the time skip check might have done drastic things that invalidate this step

        # ESTIMATE THE FINALDICT ENTRY FOR THE TROUBLEMAKER WORD - SOMEHOW!***


        # next pass starts from next index
        newStartIndex = newStartIndex -1

        # GET RID OF THE BIT THAT WILL BE REGENERATED IN NEXT PASS
        del finalDict[newStartIndex:] # python is good for this kinda thing, even ifthis syntax looks meaningless

    # ---------------------------------------------------------


    if newIndexSet == True:
       # finally we note that because the word list is ordered forwards but iterated bacjwards, the index is actually...
        newStartIndex = len(wordList)-1-newStartIndex # if it goes below 0, the next pass won't happen, so dont need to catch that here
        # and also note we can't do this without that if tur statement because we rely on the value being -1 to mean that things are fine. yeah... this is getting messy...
        
    return finalDict, newStartIndex


def CompareBestFinalDictToActualScript(bestFinalDict, wordList): # thing that compares what the script will be according to finalDict, versus what it should be, using Levenstein distance
    ourScript = ""
    realScript = ""
    for x in reversed(bestFinalDict):
        ourScript += x["word"] + " "
    for x in wordList:
        realScript += x + " "
    ld = GetLevensteinDistance(ourScript, realScript)
    print(f"Transcript segments selected vs original script similarity level: {ld}%")

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

def SaveNewTranscript(path, entries): # copilot provided function to output our finalDict list in teh same format as the transcript input. simple enough, python is good for this.
    try:
        with open(path, "w", encoding="utf-8") as f:
            for item in entries:
                line = f"{item['start']}\t{item['end']}\t{item['word']}\n"
                f.write(line)
        print(f"Aligned Transcript saved at {path}")
        
    except:
        print(f"Failed to save transcript at {path}")
    


