# stuff for AutoEdit to use

import re
import numpy as np
from collections import Counter

# first we need a function that will take our transcript file, and turn it into a structure with three values per entry: start time, end time, and the word/phoenem.
def LoadTranscript(path):

    # *** this program assumes the transcript entries are either 1 word or less, but the openVINO plugin tha tmakes them doesn't do thsi by default, and can have all sorts of block
    # sizes. thus we can either a) warn the user if the word entry below contains a space/multiple words, or b) try to split input up into words and estimate the timestamps
    
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            index = 0
            for line in f:
                parts = line.strip().split("\t") # split on \t means tab. can try no arg to split on whitespace, which may also fit the way the file is outfrom from OpenVINO.
                
                if len(parts) != 3: # check for the line being invalid - should never happen since the output is standardised
                    continue
                
                start, end, word = parts # define 3 variables from the 3 things we should have got from our split. we expect number, number, string

                word = re.sub(r"[^\w\s]", "", word).strip().lower() # gonna work all in lower case for this, and no punctuation (note this may leave word as empty string) *** may want to ignore the empty rows depending on how the final recording edits end up sounding with these left in
                
                entries.append({
                    "start": round(float(start), 5),
                    "end": round(float(end), 5),
                    "word": word,
                    "transIndexList":[index],
                    "wordIndex":0
                }) # we're making a list of dictionaries, with 3 keys, which lets us call them back with something like entries[100]["start"] tp get the start numebr for row 100.
                # added the rounding because sometimes there is an annoying 00000001 tick on these, which we can ignore

                # that transIndexList one is just there because other dict structures copy the structure of these transcript dictionaries,
                # and they need will store the transcript index they correspond to. especialy as the dict can sometimes be copied wholesale into the result dictinoary lists.
                # and its a list because ultimately the finalDict entries might contain a list of several indicies for a single word, since they can compound. most of the time it will
                # be a list of 1 entry though
                # the word index one will be used to link confirmed transcript entries tothe word in the script they are / are a part of, which is handy for various things
                index += 1

            # -----------------------------------------------------------
            # RESOLVING A SORTING ISSUE FROM IMPERFECT TRANSCRIPTION PROCESS
            # once we've got our transDict here, there is a problem: i have noticed the transcription output from openVINO sometimes gets 2 small words or phonemsn that are very
            # close together mixed up. what it does is given then the same start time, but the correct tiemtimes, whoever because its all sorted by start time, it ends up having them
            # in the wrong order. so, i will boldly assume that the end times are all correct, at least, as that appears to be true from what i've seen so far. thus i will switch the
            # list to be sorted by end time - ALSO ASSUMES END TIMES ARE ALL DIFFERENT, which in my experience is a solid assumption, open vino works properly in this regard
            entries.sort(key=lambda d: d["end"]) # i think taht's all it takes, more python wizardry, provided by copilot
            # HOWEVER we also need to update teh self referencing indicies now too
            i = 0
            while i < len(entries):
                entries[i]["transIndexList"] = [i]
                i+=1
            # glorious
            # -----------------------------------------------------------
            
    except:
        print("Failed to load transcript.")
        return []
        
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
        return []

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
        print(f"\nScript estimation:\n{scriptEstimation}")


def PrintActualScript(wordList):
    # shows what the script should be accord to teh wordList (list of strings)
    script = ""
    for x in wordList:
        script += x + " "

    print(f"\nActual script:\n{script}\n")

def ShaveFinalDictToConfirmedMatches(finalDict, wordList, bestFinalDict):
    # shall return the finalDict entries that create a good match with teh script up to a given point, and an index related to that point
    # DEPRECIATED IMPORTANCE - this used to be part of the automatic error handling, but we now rely on the user for corrections. this code still runs
    # but as a backup check that will mainly serve to cut out erroneous parts caused by bad user input, so they can be searched for another on a new pass through the main loop

    # The logic of thsi process is to compare the finalDict to the part of the script it is mean to be match up to, and cut it off at a point where X number of errors are found in
    # a row, since that indicates something has broken and we need to try again (which now means probably trying to get user input again).

    newStartIndex = -1 # this default valueu will halt the main loop if we find the match with the script is 'good enough' the whole way. what the words 'good enough' mean are
                        # the main thing we need to decide in this function

    newIndexSet = False # matters right at the end

    # note, the dict is backwards, bu tthe worldList is forwards, so we need to use...
    script = wordList.copy()
    script.reverse()

    # ERROR RESOLUTION VARIABLE
    # this is a key concept. we need to decide how many errors need to be a row for a suitable break in the coparison to have been found. all i know is that small numbers of errors
    # resulting from weird names, potentially with many words, is entirely possible, so this number needs to be long enough to let such things through, to avoid having way too many
    # passes. the main goal is detecting errors that mess everything up, like searching for 'and' where the transcript mistakenly says 'an' and then landing on one way ahead in
    # the script, which then will oblitarate the main loop. the user input should prevent this, if done perfectly, but it very well may not be done perfectly, desu nee?
    errorRes = 3

    # also note this function ignores the fact that the correct word can be taken from the wrong position - it will pass this check wrongly, but that post-user input checks are more
    # advanced and will target those before thsi code even runs. again THIS CODE IS FOR EMERGENCY USE and doesn't fully rectificy problems!

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

        # we can also do a basic transcript Dict check, where if the transdict index ever goes up, it (probably) means a user input was made AFTER an unhandled mistake occured. this is
        # handled properly by the post-user input checks, but we can put a rough parallel check here
        if i > 0 and finalDict[i]["transIndexList"][0] > finalDict[i-1]["transIndexList"][0]:
            newStartIndex = i - 1 # where to search from here is nebulous, as it just means SOMETHING is wrong, anywhere before this point.
                                  # i'll just go back 1 in the hopes of triggering a user input, as it was probably a mistakenuser input that caused
                                  # the transcript index to jump in a way that didn't trigger the usual corrections of earlier errors #somehow
            print(f"Transcript Index increase found in FinalDict analysis. (Index: {finalDict[i]['transIndexList'][0]}, Word: {finalDict[i]['word']}. FinalDict will be cut to this point to begin the next pass.")
            newIndexSet = True
            break
        
        i = i+1 # end of main loop
        # -------------------------

    # ----------------------------------------------------------
    # AMMENDMENT
    # now, if start index isn't -1, we ideally need to identify the troublemaker and handle it specially, and then start the next pass from the next word
    # however, since no complete way to know the troublemaker has been developed yet, we can't do much but skip it and try to get the rest right for the time being

    if newStartIndex > -1 and len(finalDict)>0: # second condition is because the time skip check might have done drastic things that invalidate this step
        # originally there would have been some estimation of the correct finalDict here, but this idea has ultimately been replaced by the user input step, which happens
        # before this point. this function remains only as an additional check / backup / emergency prayer mode

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
                line = f"{item['start']:.3f}\t{item['end']:.3f}\t{item['word']}\n"
                f.write(line)
        print(f"\nAligned Transcript saved at {path}")
        
    except:
        print(f"\nFailed to save transcript at {path}")


def CheckNewWordContext(wordList, wordListIndex, transDict, finalDict, bestFinalDict, transIndiciesUsed, fuzzyMatch = False):
    # big helper function that will see whether a word added to the finalDict looks good according to the recently other used transcipt dict entries, which should, if all is correct, look
    # a lot like the prior entries in the script when jammed together
    # use optioanl fuzzymatch arg to make it use the fuzzy match comparison to decide it things are 'equal enough'

    # get the relevant transDict entries
    tempTransDict = GetConfirmedTransDictList(transDict, finalDict, bestFinalDict)

    # we will make a string of a given length from this new transdict, taking only indexes that are higher than the newlyAddedTranIndex (which will be all of them in a perfect world, not guaranteed Id on't think)
    contextWindowSize = 10

    startIndex = GetTempTransDictIndexForTransIndex(tempTransDict,transIndiciesUsed[0]) # find where to start buiding from (helper below)

    # --------------------
    # startIndex NOT FOUND ESCAPE HATCH + REPORT
    if startIndex == None:
        # it means there was no entry in any finalDict that has a first transIndexList entry that corresponds to teh first of our list of used indicies. this is highly suspiocys,
        # and might be impossible under non-erroreous conditions
        print(f"During context check for [{wordList[wordListIndex]}], the finalDict was not found to contain any entries that logged the use of transcript index {transIndiciesUsed[0]}. "
              + "The context check could not go ahead, and something is probably wrong in the recording of transcript indicies.")
        return False
    # -------------------

    i = 0
    transContext = ""
    # with teh transcript, we are searching down phonems that need to be appended frontally to make our words
    while startIndex + i < startIndex + contextWindowSize and startIndex + i < len(tempTransDict):
        transContext += tempTransDict[startIndex+i]["word"]
        i += 1
        
    # ---------------------------------------------------------
    # GET THE SCRIPT CONTEXT
    # this one is easier
    wordContext = ""
    i = 0
    startIndex = wordListIndex
    while startIndex + i < startIndex + contextWindowSize and startIndex + i < len(wordList):
        wordContext += wordList[startIndex+i]
        i += 1

    # ----------------------------------------------------------
    # COMPARE AND REACT

    # by now we have 2 strings, which are non-whitespace non-puncation characters written backwards. lets reverse them for debugging sake during this

    # the wordContext will probably be longer, because its full words. so we compare against the the beginning of wordContext up to len of the transContext
    # since in prinicpal i could be the other way around, i will trim for the shorter case either way
    if len(wordContext) > len(transContext):
        wordContext = wordContext[:len(transContext)]
    else:
        transContext = transContext[:len(wordContext)]
    
    # ARE THEY THE SAME?
    # as a side note, in thsi comparison you might think that user-confirmed words will be an issue. when a word is in the script but not correctly transcribed, the user picks out
    # some transcript entries for it. this is now a correct match but make theprior context appear wrong for subsequent word when this scan runs. BUT i shall actually be updating the
    # transcript list with user=provided confirmed word from the script, such that things run smoothly. just so you know
    if fuzzyMatch == True:
        return FuzzyMatchWords(transContext,wordContext,False)
    elif wordContext == transContext:
        #print(f"Context report for {wordList[wordListIndex]}.\nTranscript Context: {transContext}\nScript Context:     {wordContext}") # testing only
        return True
    else:
        print(f"Context Error found for {wordList[wordListIndex]}.\nTranscript Context: {transContext}\nScript Context:     {wordContext}")
        return False
    # -------------------------------------------------------------


# lil helper for the above fcuntion
def GetTempTransDictIndexForTransIndex(tempTransDict, targetTransIndex): # copilot did teh basic idea, and i believe in it
    for i, d in enumerate(tempTransDict):
        if d["transIndexList"][0] == targetTransIndex: # all the transDict entries have that idnex list as a single entry, that being their own index
            return i
    return None


def GetConfirmedTransDictList(transDict, finalDict, bestFinalDict):
    # makes a list of dictionaries, like the 'transDict' object, but only containing rows that are currently believed to be confirmed matched.

      # make a tenp version of the bestfinalDict + finalDict i.e. th ebest final result we have available
    tempDict = bestFinalDict.copy()
    tempDict.extend(finalDict)

    # -----------------------------------------------------
    # GET THE TRANSCRIPT CONTEXT
    # we need a versino of the transDict that only contains the indicies which have been used so far. first we can use our tempDict to see all the indicies we need
    tIndexList = []
    for x in tempDict:
        for y in x["transIndexList"]:
            tIndexList.append(y)

    # we also need everytrhing strictly sorted in transIndex order. we also need to remove repeats (the set does this), which i think can happen legitiamtely but not sure.
    tIndexList = sorted(set(tIndexList))

    # now filter a copy of the transDict. luckily python makes this real easy
    tempTransDict = [transDict[i] for i in tIndexList]

    return tempTransDict

def CheckFinalDictForTroublemakers(confirmedIndex, finalDict):
    # returns false + the finalDict index no if any final dict entry has a transIndex earlier than the confirmedIndex. for logic, see the place this si called in the main script

    i = 0
    troublemakerIndex = -1
    troublemakerFound = False
    
    while i<len(finalDict): # we only care about the FIRST instance where confirmedIndex < transIndex, as all future ones are assumed to be caused by this first troublemaker (first because the finalDict is in reverse order with respect to script)
        if finalDict[i]["transIndexList"][0] < confirmedIndex: # note only bothering to check first index of cases wherethey are lots here, that should be enough
             troublemakerIndex = i
             troublemakerFound = True
             break
        i += 1

    return troublemakerFound, troublemakerIndex

def FuzzyMatchWords(compareWord, scriptWord, showResult = True):
    # if two words are close enough, we shall delcare them matched. what 'close enough' means shall be defined in here

    # i want longer words to require a little less similarlity. we can't have 'hi' and 'hit' be matched because they are only 1 change different, but we go want 'osiriss' and 'ossiris'
    # lets require 100% match up to 4 characters, 80% at 5 characters, and see hwo it goes

    # the problem with all this is that the transword can have 1 character words appended to it, like if the word checked befoer it is 'i' or 'a' then we will end up with
    # comparisons like worda, wordi, which will go through as close enough, using up more transindexes then expected. potentially, chaos? or acceptable risk of fuzzymatching?
    # well teh risk will have to be acceptable, and we shall see how the ultimately resilts are effected.

    requiredMatch = 100
    if len(compareWord) > 4:
        requiredMatch = 80

    score = GetLevensteinDistance(compareWord, scriptWord)

    if showResult == True:
        print(f"Fuzzy Match Check: {compareWord} vs {scriptWord} - {score}") # for testing

    if score >= requiredMatch:
        return True
    else:
        return False
    

def GetListOfAllCommitedTransIndexes(finalDict, bestFinalDict): # NOT USING THIS ANYMORE, WILL LEAVE JUST IN CASE I CHANGE MY MIND
    # returns a list of numbers, all teh indicies that are being used in teh finaldicts. having this to hand will let us look back at previous sections of the transcript
    # and looking for skipped over words with reduced risk of accidentally re-taking a word already used. make sense? good.

    indexList = []
    for x in bestFinalDict:
        indexList.extend(x["transIndexList"])
    for x in finalDict:
        indexList.extend(x["transIndexList"]) # will often be adding a single value, but sometimes its a handful
    
    return indexList # in princpcal can return empty list here


def IterateDictTransIndicies(finalDict,bestFinalDict, transDict, insertedIndex):
    # for use when a new index is added to teh transdict by some automated code. we need to find all refernces to indexes higher than than in the dicts and iterate them,
    # since the transidct list is now 1 index longer

    # lets be lazy

    for x in finalDict:
        i = 0 # found ou tthe h ard way that a for y in list y +1 method dont' work!
        while i < len(x["transIndexList"]):
            x["transIndexList"][i] += 1
            i += 1

    for x in bestFinalDict:
        i = 0
        while i < len(x["transIndexList"]):
            x["transIndexList"][i] += 1
            i += 1

    # for the transdict we can be extra sure by just reseting the index to be the new correct one every time this update is called
    i = 0;
    while i < len(transDict):
        transDict[i]["transIndexList"] = [i]
        i += 1


def GetKeywordsList(transcriptDict, wordList, debugMode):
    # a function that will return a list of words that appear in the transcript and script only 1 time, which has uses in our troublemaker hunting efforts

    # first i need all the transcript words in regular list format, same as wordList
    transWordList = []
    for x in transcriptDict:
        if x["word"] not in ("", " "): # just to keep it easier, as some entries are blank, shouldn't matter but lets be safer
            transWordList.append(x["word"])

    # EXTRA STEP TIME
    # we also need to only consider words that are not part of any larger words also in the list. the reason is arises from the following case: Bes. The word Bes was in a script
    # as a name, and appeared in the transcript as part of thebes, as 2 entries 'the, bes'. meanwhile the real transcipr for Bes was 2 entries, 'B, ess'. transcripts are weird.
    # the result is an infinite loop of finding the troublemaker over and over and looping back to where bes is meant to be in the script.
    # one consideration to combat this is to throw out from teh word list any word that is contained within another word.
    # *** could also have a minimum length requiremenet to reduce chance of error?
    newWordList = []
    for x in wordList:
        safeToUse = True
        for y in wordList:
            if x!=y and x in y: # e.g. if bes is in thebes, it won't be used, reducing the chance of this annoying error
                safeToUse = False
                break;
        if safeToUse == True:
            newWordList.append(x)
    # we end with a list of words that are not containing in any other words.
    if debugMode == True:
        print(f"Number of words not containing other words in script: {len(newWordList)}")
    # --------------------------------------------------------------------------------
    # Make our unique pairs list - copilot vibecode alert
    # copilot told me to use this method with teh 'counter' function, imported at the top
    c1 = Counter(transWordList)
    c2 = Counter(newWordList)

    # items that appear exactly once in each list
    unique1 = {x for x in transWordList if c1[x] == 1} # magically gives the entries that only appear once
    unique2 = {x for x in newWordList if c2[x] == 1}

    if debugMode == True:   
        print(f"Keyword List: {list(unique1 & unique2)}") # testing

    # intersection of the unique sets
    return list(unique1 & unique2) # this will magically give us the things that are in both lists

def TroubleMakerCheckAndHandling(uiBall, transIndex, finalDict, superGuessMode = False, debugMode = False):
    # outsourced modular version of trouble maker handling, in which the final dict is checked for entries being out of order compared to the transcript, and then we
    # react depending on the use mode. transIndex should be the transcript index of something you are certain has been matched correctly.

    returnWordIndex = -1
    returnTransIndex = -1

    # after a user input or keyword detection, we can go through our final dict and see if any words places in earlier were from a lower trans index (ie. they were supposed to appear later in the search).
    # these are the mythical TROUBLEMAKERS, where a script word was transcribed wrong, but correctly later on, or mistakenly transcribed from another word later on.
    # in these cases, we ask teh user to manually locate the trouble maker, then roll the wordIndex back there, strip our finalDict down, and restart our process from the next
    # word. this should get everything back on teh right track, and we can repeat this if it happens again.
    troublemakerFound, troublemakerIndex = CheckFinalDictForTroublemakers(transIndex, finalDict)

    if troublemakerFound == True:
        x = finalDict[troublemakerIndex]

        if superGuessMode == False: # no communication with user in super guess mode, this is silent error correction (outside of debug info I suppose)
            print(f"\nWarning: A word, [{x['word']}] previously found in the transcript may have been taken from the wrong context, or been mistaken for another word." 
                  " Please confirm the correct instance of it.")
            
            # for where the UI needs to point, we can hedge that if the word BEFORE the trouble maker was right, then the real thing the troublemaker was supposed to detect is near that
            if troublemakerIndex>0:
                uiBall["indexUI"] = finalDict[troublemakerIndex-1]["transIndexList"][0]
            else:
                uiBall["indexUI"] = troublemakerIndex
        else:
            if debugMode == True:
                print(f"Super Guess Mode discovered a troublemaker word: [{x['word']}]. It's true location will be guessed, and the processing will be reset to this position.")
            #print(f"Full details of troublemaker entry: {x}") # testing
            #wait = input("Press Enter to continue.")


        # now we cut everything from the troublemaker onwwards out of the finalDict list, reset the wordIndex to pretend we're looking for that one again, then head back
        # to teh user interface to look for the replacement
        wordIndex = x["wordIndex"] # we will then nartuarlly cycle on from here at the end of current wordIndex loop, and it will all be smooth sailing. :D :D :D :D ;D
        uiBall["wordIndex"] = wordIndex
        del finalDict[troublemakerIndex:]  # nifty python way of clipping the list

        #print(finalDict) # testing
        ## testing, just wanna see the context readouts after our deletion
        #a, b = utils.CheckNewWordContext(wordList, wordIndex, transcriptDict, finalDict, bestFinalDict, finalDict[-1]["transIndexList"])
        
        # USER INPUT OR GUESS MODE GUESSING
        if superGuessMode == False:
            newTransIndex = userInterface.ProcessUserInput(uiBall["wordList"][wordIndex], uiBall) # this should sort things out, if the user can be trusted LOL
        else:
            # we need to guess.
            # guess logic is simple that the word will be added with timestamps based on the previous word (assuming its correct, hmmm), and we also update the transcript to
            # make our guess look right so it will all pass future context checks. we have a function for this, since it can be called from elsewhere too.
            newTransIndex = SuperGuessWord(finalDict,uiBall["wordList"][wordIndex],wordIndex,uiBall["bestFinalDict"],uiBall["transDict"], debugMode)

        if newTransIndex>-1: # IF THE USER INPUT OR SUPER GYESS CHANGES SOMETTHING, EG THEY DIDN'T CANCEL / SKIP THE WORD
            returnTransIndex = newTransIndex
            returnWordIndex = wordIndex

    # return where we are in the word list now, and where we are in the transript now
    return returnWordIndex, returnTransIndex

def SuperGuessWord(finalDict, word, wordIndex, bestFinalDict, transcriptDict, debugMode = False):
    # takes a word and puts it in the finalDict and the transcript, using previous entry in finalDict as a guide for the timings. we are just estimating where the word is,
    # and trying to get any label to appear somewhere near the right place.
    # returns a transIndex for where to serach next i.e. the previouslySearchedtoIndex thing
    
    lastEntry = finalDict[-1]
    guessIndex = lastEntry["transIndexList"][0]
 
    #make our fake transcript entry so the context checks will play nice with our skip
    entry = {"start":round(lastEntry["start"] - float(0.1),5),"end":lastEntry["start"],"word":word,"transIndexList": [guessIndex],"wordIndex":wordIndex}
    transcriptDict.insert(guessIndex, entry) # index changes handled a few lines down
    # we arbitrarily make the entry 0.1 second long, just want something to appear in the final label file without messing up any proper order of timing
    # due to inserting a new index into a list whose index numbers are stored EVERYWHERE- SIGH - we need to go through the finaldict, bestFinalDict,
    # and transDict and iterate all the recorded transcript indexes up by 1 if they are larger than guessIndex, sorry lololololol
    IterateDictTransIndicies(finalDict,bestFinalDict, transcriptDict, guessIndex)

    finalDict.append(entry) # to complete the skipping process in a 'everything is fine' looking way, to add our new perfect dummy transcript entry as the finalDict entry for thsi word. all done!

    if debugMode == True:
        print(f"Super Guess Mode added a dummy transcript entry at index {guessIndex}: {entry}") # testing

    return guessIndex + 1 # +1 to keep our safety tradition of starting next search on the 'end' of the old one

#################################################################################################################
### VIBECODE ZONE ### ############################################################################################

# i want to try a new typoe pf transcript, and i have asked copilot to make afunction that will convert it to be the same format as the old one
def convert_transcript_file(input_path, output_path):
    """
    Convert a transcript file from the new format:

        04:59.490 --> 04:59.670
        has

    Into the old format:

        299.490000    299.670000    has
    """

    def time_to_seconds(t):
        # Convert "MM:SS.mmm" or "HH:MM:SS.mmm" into float seconds
        parts = t.split(":")
        if len(parts) == 2:
            # MM:SS.mmm
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:
            # HH:MM:SS.mmm
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            raise ValueError(f"Invalid timestamp format: {t}")

    # Read the entire file (keeping in mind the file path may have been given incorrectly, so this may error out)
    try:
        
        with open(input_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]

        # ⭐ Detect format
        is_new_format = any("-->" in line for line in lines)

        if not is_new_format:
            print("Transcript already appears to be in correct format — skipping conversion.")
            return


        output_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Look for timestamp lines
            if "-->" in line:
                start_str, end_str = [x.strip() for x in line.split("-->")]
                start = time_to_seconds(start_str)
                end = time_to_seconds(end_str)

                # Next line is the text - (can be nothing though)
                j = i + 1
                if j >= len(lines):
                    break
                text = lines[j].strip()

                # Build old-format line
                output_lines.append(f"{start:.6f}\t{end:.6f}\t{text}")

                # Move past the text line
                i = j + 1
            else:
                i += 1

        # Write the converted transcript
        with open(output_path, "w", encoding="utf-8") as f:
            for line in output_lines:
                f.write(line + "\n")

        print("Transcript format conversion completed.")

    except:
        print("Transcription conversion checks failed - transcript may not be available at the given path.")
############################################################################################
