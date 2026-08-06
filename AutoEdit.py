# ==========================================================================
# ###RAW RECORDING AUTO EDITOR ###
# For converting a recording that contains all the material from a given script into a recording that contains ONLY the script, by removing all failed takes.
# Requires OPENVino Whisper label output from Audacity as the starting transcript to use (see readme for full instructions).

# This script will
# 1) take a timestamped word-by-word transcript of a recording and the intended script as input
# 2) compile a list of all the words and timestamps, and all the indidivudal words in the script
# 3) search from the end of the lists, creating list based on the logic of the final word's final utterance in the script being its correct use, then move on to next word and repeat
# 4) create a reliable list of where all the desired 'final take' words are, and estimate where all the mismatched or miss-transcribed ones are as well
# 5) feed this list to a functin that uses ffmeg to make an audio files based on the timestamps, given a reference file (i.e. the raw recording the transcript was from)

# *** EXTENDO FEATURE DESIRE: allow it to be clever about not working with words that are in the script but aren't voices. at it stands, the script must be exactly what is desired in the
# final recording (no titles, unvoiced headings, directions, anything like that).

# ===========================================================================
import utils
from pathlib import Path
debugMode = True

# define our paths to files *** this may be done with parameters or in a GUI in teh future
basePath = Path(__file__).parent
pathToTranscript = basePath / "testing" / "script1.txt"
pathToExpectedScript = basePath / "testing" / "The Actual Text.txt"

transcriptPhoenemsToSearchBack = 5 # how many entries in the transcriptDict can be combined in the earch for a match with a given word (see notes below)

# ===========================================================================

# IMPORTS

transcriptDict = utils.LoadTranscript(pathToTranscript)
wordList = utils.LoadExpectedScript(pathToExpectedScript)

#if(debugMode == True):
 #   print(transcriptDict)
  #  print(wordList)

# ===========================================================================

# MAIN SEARCH LOOP

# loop logic steps:
# take the last word in our word list
# take the last 'word' attribute of the transriptDict
# if they match, we add that transcriptDict entry to an identical finalDict. then we remove the entry from the wordList and transcript Dict, so the next search begins one step earlier
# if they don't match, we need to check whether combining the transcript word with the previous word will create a match instead, because the transcript word can be phoenems, or
# whitespace like words like "-" in "post-haste".
# if scanning back a certain number of entries still doesn't give us a match, we shall move up one entry and repeat the search pattern.
# thsi repeats until the whole thing has been searched. then, if still no finds, the word is declared to not be in the recording (which is allowed as script may contain unvoiced elements).
# the word is dropped, we move onto the next word, and the whole thing repeats.
# we end up with a finalDict listing, maybe, somehow, all the timestamps needed to form a complete sequence of words that will match the script.

finalDict = transcriptDict.copy()
finalDict.clear() # empty version of the transcriptDict that will contain our matched entries
maxSearches = transcriptPhoenemsToSearchBack
wordIndex = len(wordList)-1
missingDict = finalDict.copy() # another parallel output will hold datat on words that weren't found in the transcript, so we can sae the timestamps from nearby words and try to keep this area in teh recording *** flesh this out

previouslySearchedToTransIndex = len(transcriptDict)-1 # this is the 'read-head' point we searh forward from
# due to errors in the imperfect transcription process, sometimes the search can jump too far ahead in teh search for some strange spelling of a word and perhaps find it,
# so the process is inherently not able to deliver perfect results, and in fact is basically CERTAIN to miss things and get things wrong, unfortunately. We shall have to implement
# measures to try to preserve all the areas where there is uncertainy for manual review, and potentially have a repeat / refinement stage to try to programatically correct the
# reuslt of the first run through ****


while wordIndex > -1:
    checkword = wordList[wordIndex] # final word in list is the next word to look for
    checkWordFound = False
    if debugMode == True:
        print("Searching for word: " + checkword)
    # ----------------------------------------------------------------------------------------
    # PER CHECKTRANSWORD LOOP
    # in which we try to concatened it with previous entries a load of times and cgeck again, before moving on check the next transword in the next iteration of the loop

    # define these outside of the loop because we need to record it afterwards
    transIndex = previouslySearchedToTransIndex-1 # this is recorded upon a succeful find so teh next word loop starts in the relevant place
    checkTransWord = "" 
    startTime = 0.00
    endTime = 0.00

    while transIndex > -1:
        checkTransWord = "" # reset
        # -------------------------
        # Concatination with earlier entries check loop
        x = 0
        
        while (x < maxSearches) and (transIndex - x > -1):         # note that we need the second check to avoid problelms when we've shaved the transcriptDict all the way down
            checkTransWord = transcriptDict[transIndex-x]["word"] +checkTransWord # frontally concat the previous transWord (or read the first one when x = 0) to see if they compound to make the checkwork on the next loop of this while

            #print(f"x={x}, Checkword: [{checkword}], checkTransWord: [{checkTransWord}]") # testing purposes

            # do we have a match right now?
            if(checkword == checkTransWord):
                checkWordFound = True

                # now we put together the dictionary entry we need, combining the transcriptDict entries if we had several
                # it's the end time of the transIndex, up to teh start time of transINdex - x
                wordForFinalDict = checkTransWord # it already the full string we need
                endTime = transcriptDict[transIndex]["end"]
                startTime = transcriptDict[transIndex-x]["start"]
                if debugMode == True:
                    print(f"Found: [{wordForFinalDict}] from {str(startTime)} to {str(endTime)}")
                previouslySearchedToTransIndex = transIndex-x # record the index, future searches only need to look earlier than this
                break # leave this search loop
            
            else:
                # if no match, we can check to see if the characters are the end of the checktranswork are the same as the ones at the end of the checkword
                # if so, its worth concantinating more stuff to see if we can get the full match
                testString = checkword[-len(checkTransWord):] # last x characters of checked work where x is the length of the current checkTransWord
                if(testString != checkTransWord):
                    x = maxSearches # not gonna match no matter how much we concat, so forget this concat loop thing, let it move on
                
            # assuming we don't have a match, repeat loop, it will do the above montioned concatincation and recheck
            x = x+1
        # ---------------------------

        # now, if we have a find, we can break the loop and move on to the next base checktransword. oetherwise, we proceed to process our found records
        if checkWordFound == True:
                        break # breaking the transIndex > -1 loop
        else:
            transIndex = transIndex - 1 # loop continues
    # ---------------------------------------------------------------------------------------

    # now we've eitehr checked the whole transcriptDict and not found it, or we did find out
    if checkWordFound == True:
        # lets put it in our finalDict (not its actually a list of dictinoaries)
        finalDict.append({
                    "start": float(startTime),
                    "end": float(endTime),
                    "word": wordForFinalDict})

    else:
        print(f"Didn't find word: [{checkword}]")
        # in this case, we add the missing word to a dcinotary and note the start time of the last found word as being the likey end time of the thing that can't be found
        lastStartTime = finalDict[len(finalDict)-1]["start"]
        missingDict.append({"start": 0, "end":float(lastStartTime),"word":checkword})

    # here we are are the end of the loop for a given word.
    wordIndex = wordIndex-1

# ====================================================================================================
# DICTIONARY PROCESSING

# By now, we have our finalDict, a list of dictionaries that contain all the correct start and end times in reverse order, plus another dicinotary with only the estimated
# end tines of words that were in the script but weren't found (often names or things the transcripts will likely get wrong)

if debugMode == True:
    print("Final Dictiionary List:\n")
    print(finalDict) # for testing
    print ("Missing Dict List:")
    print (missingDict)

# -------------------------------------------------------------------------
# MISSINGDICT ENTRY START TIME GUESS AND MERGE INTO FINALDICT
# we need to slip all the missing dictionary entries into the final one, assigning relevant start times
# so we find the entry in the finalDict that has the startTime matching the missingDict endTime, and then take the finalDict endTime from the entry 1 index earlier
# to keep things all in the order we intended to output them in, we'll do a list insert on finalDict (remembering that finalDict is actually a list of dicts, lolololol)

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
        
# ------------------------------------------------------------------------------
#if debugMode == True:
 #   print("Updated Final Dictionary List:\n")
  #  print(finalDict) 

# and since final dict is backwards, let's finally reverse it
finalDict.reverse()

# conclude the data gathering by printing out the script (no punctuation unfortunately) according to finalDict

scriptEstimation = ""
for x in finalDict:
    scriptEstimation += x["word"] + " "
print(f"Final script estimation:\n{scriptEstimation}")

# that's the end of our word processing. now we move on to audio processing with teh data we've gathered.
# =====================================================================================================
