# ==========================================================================
# ###RAW RECORDING AUTO TRANSCIPTION HELPER ###
# For transcribing a recording that contains all the material from a given recording in a way that it transcribes ONLY the parts of the recording corresponding to the script
# Requires OPENVino Whisper label output from Audacity as the starting transcript to use (see readme for full instructions).

# This is part 1 of a 2 part autoedit process, where the second part will edit the audio file itself without returning to audacity. whoever the transcript created by part 1
# can be imported into audacity, then youcan use audacity's own feature where it cuts a recording by labels to get yourself an automatically cut version, similar to what
# part 2 is / was envisioned to achieve.

# This script will
# 1) take a timestamped word-by-word transcript of a recording and the intended script as input
# 2) compile a list of all the words and timestamps, and all the indidivudal words in the script
# 3) search from the end of the lists, creating list based on the logic of the final word's final utterance in the script being its correct use, then move on to next word and repeat
# 4) create a reliable list of where all the desired 'final take' words are, using user input to confirm where things that can't be automatically placed are supposed to be

# *** EXTENDO FEATURE DESIRE: allow it to be clever about not working with words that are in the script but aren't voices. at it stands, the script must be exactly what is desired in the
# final recording (no titles, unvoiced headings, directions, anything like that).


# *** NEXT THING TO TRY:
# if we force the user to manually select at least some words, it will let our post-checks trigger. it is essential it happen at least once, so perhaps the final word will always ask
# so that the check is performed on teh maximum possible amount of the final result.

# another category of things to try is fuzzy matching to let fewer things be considered missing

# ===========================================================================
# HEADER AND CONSTANTS
import utils, userInterface # the other scripts in this program
from pathlib import Path

debugMode = True

# define our paths to files *** this may be done with parameters or in a GUI in teh future
basePath = Path(__file__).parent
pathToTranscript = basePath / "testing" / "script1.txt"
pathToExpectedScript = basePath / "testing" / "The Actual Text.txt"
#pathToAudioFile = basePath / "testing" / "audio.mp3" # this script doesn't need to interact with the audio file as it stands, we start from a user-provided transcript and give another one back
outputFolder = basePath / "testing"

transcriptPhoenemsToSearchBack = 30 # how many entries in the transcriptDict can be combined in the earch for a match with a given word (see notes below)
# only reason to limit this is performance, but because i have improved the part that combined phonems so that it breaks the loop when it sees its not going anywhere, there is now
# not much to be lost in allowing big searches - they will only actauly happen in cases where they are needed

# ===========================================================================

# DATA IMPORTS AND INITS

transcriptDict = utils.LoadTranscript(pathToTranscript)
wordList = utils.LoadExpectedScript(pathToExpectedScript)

# we define a dictionary that will hold useful refs to allow our UI script to operate alongside this main script, mainly for neatness,
    # even though it does invoke the unneatness of using this ball #refusingToUseOOPBecauseIWantToLearnHowToDoThingsAnotherWay
    # VERY IMPORTANT: remember its a mix of refs and values, so teh dicts are refs can be udpated freely, the indicides are value copies so you can't transmit changes automatically
uiBall = {"wordList":wordList, "transDict":transcriptDict, "finalDict":{}, "indexUI":0, "wordIndex":0}

#if(debugMode == True):
 #   print(transcriptDict)
  #  print(wordList)

# ===========================================================================

# MAIN SEARCH LOOP

# A GUIDE TO THE LOOP LOGIC:
# (note that all the loops run backwards, because of the general rule that the 'final' instance of something in the raw recording is always preferable.
#   going backwards makes things easier to handle if this assumption is held to).

# Nested loop order: 1) Unconfirmed Segment passes from the latest word we haven't confirmed the timestamp for.
#   2) We loop over words in the pass 3) tested against phoenems in the transcript and optionally 4) testing increasingly large compound phoenems in the transcript

# the highest level loop, the 'unconfirmed segment pass', performs the entire transcript serach procedure below, but starts at an earlier and earlier word in teh script each
#   time, letting aside the parts on the end that are confirmed to be correct after each pass. this is now mostly a vestige of previous efforts to automate the finding and
#   correction of errors, but that is now done by the user, so this 'passes' loop will usually only actually run once. i will leave it in place as a failsafe and because i don't
#   want to mess things up #refactoring

# Here is one complete 'pass':
# take the last word in our word list
# take the last 'word' attribute of the transriptDict - this can be a phonem like '-' or may be blank, if it was only a punctation mark that was removed by punctiation filter on import
# if they match, we add that transcriptDict entry to an identical finalDict. then we remove the entry from the wordList and transcript Dict, so the next search begins one step earlier
# if they don't match, we need to check whether combining the transcript word with the previous word will create a match instead, because the transcript word can be phoenems, or
# whitespace like words like "-" in "post-haste".
# if scanning back a certain number of entries still doesn't give us a match, we shall move up one entry and repeat the search pattern.
# thsi repeats until the whole transcript has been searched. then, if still no finds, the word is declared to not be in the recording
# non-found words go into a missingDict collection for later processing - we cannot ignore them, as it is likely that some words appear in the transcript differently how they are
# used in the script (e.g. a scripted 'and' might looked like 'an' in the transcript, in practice). So some processing, and ultimately repeating of complete passes will be done to
# weed out such problems. UPDATE: the user will be asked to solve these problems by pointing out correct transcript elements
# with one script word now accounted for, we move onto the next word, and the whole thing repeats until all words have been looked for.
# we end up with a finalDict listing with locations of all the words, and missing dict, with all the stuff not found. there is a process where the missing word position
#   is estimated, which gives us a new finalDict.
# we compare the script that finalDict defines to the real script, and record the earliest word index from which they are an exact match.
# this index is where we start the whole process again from on the next pass (going backwards, remember).


# -----------------------------------------------------------------------------------------------------------
# UNCONFIRMED SEGMENT LOOP

startWordIndex = len(wordList)-1 # first pass will be the whole thing, and after recent user-input updates, i would expect most (all?) uses to only require 1 pass
bestFinalDict = transcriptDict.copy() # this is just to hold the right structure for the final output of the pass, and will be updated/replaced with a better versino after each pass
bestFinalDict.clear()

while(startWordIndex>-1):

    finalDict = transcriptDict.copy() # gets the right structure - NOTE THAT FINALDICT IS MORE LIKE PASSDICT, a thing holding the results of a single pass. bestFinalDict is the REAL final dict. sorry.
    finalDict.clear() # empty version of the transcriptDict that will contain our matched entries
    missingDict = finalDict.copy() # another parallel output will hold datat on words that weren't found in the transcript, so we can sae the timestamps from nearby words and try to keep this area in teh recording
    uiBall["finalDict"] = finalDict # handy ref for the ui script later
    wordIndex = startWordIndex

    maxSearches = transcriptPhoenemsToSearchBack

    previouslySearchedToTransIndex = len(transcriptDict)-1 # this is the 'read-head' point we searh forward from
    # due to errors in the imperfect transcription process, sometimes the search can jump too far ahead in teh search for some strange spelling of a word and perhaps find it,
    # so the process is inherently not able to deliver perfect results, and in fact is basically CERTAIN to miss things and get things wrong, unfortunately. We shall have to implement
    # measures to try to preserve all the areas where there is uncertainy for manual review, and potentially have a repeat / refinement stage to try to programatically correct the
    # reuslt of the first run through ****

    # ------------------------------------------------------------
    # ESCAPE CLAUSE
    # this ends the main passes loop in cases where there were so many errors that the system as 'passed' through teh whole thing but can't pass the error checks that set the
    # startWordIndex to -1 to indicate the pass done. basically things are screwed if we get here, and it is a developer objective to get here as infrequently as possible! thsi is
    # essentially critiacal error handling that means the program is broken.
    if wordIndex < 0 or wordIndex-1 > len(wordList):
        print("Auto Editor had to terminate because it cannot piece together an aligned transcript and has run out of ideas. Sorry!")
        break

    # ------------------------------------------------------------------------------------------------------
    # SINGLE PASS LOOP

    while wordIndex > -1 and wordIndex < len(wordList):
        uiBall["wordIndex"] = wordIndex # stpred for UI stuff later on
        checkword = wordList[wordIndex] # final word in list is the next word to look for
        checkWordFound = False

        # ----------------------------------------------------------------------------------------
        # PER CHECKTRANSWORD LOOP
        # in which we may try to concatened it with previous entries a few times and cgeck again, before moving on check the next transword in the next iteration of the loop

        transIndex = previouslySearchedToTransIndex-1 # this is recorded upon a succeful find so teh next word loop starts in the relevant place
        transIndiciesUsed = [] # we also need to list all indicies use in teh case of compound words, to store in finalDict for assorted reporting/degbugging purpsoes
        
        print(f"Start of search for [{checkword}] with transIndex: {transIndex})")
        checkTransWord = "" 
        startTime = 0.00
        endTime = 0.00

        while transIndex > -1:
            checkTransWord = "" # reset
            x = 0
            # -----------------------------------------------------------
            # CONCATENATION WITH OTHER TRANSWORDS LOOP
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
##                    if debugMode == True:
##                        print(f"Found: [{wordForFinalDict}] from {str(startTime)} to {str(endTime)}")

                    previouslySearchedToTransIndex = transIndex-x # record the index of the START of the concatenated word. (context check feature assumes its the start, dont change); future searches need only look later than this in the transcript
                    transIndiciesUsed = list(range(transIndex-x,transIndex+1)) # should give us all the indicies of our compond, or just 1 entry if no compound. +1 because of how range bounds works
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
                
        # ==================================================================================================================================
        # ADDING WORD TO FINAL DICT AND PERFORMING VALIDATION AND SANITY CHECKS, POTENTIALLY LEADING TO USER INPUT

        userInputNeeded = False
        contextCheckPassed = False
        
        # now we've eitehr checked the whole transcriptDict and not found our word, or we did find SOMETHING that matches it, which may or may not be the correct word in the correct context
        if checkWordFound == True:

            # lets put it in our finalDict (note its actually a list of dictinoaries)
            finalDict.append({
                        "start": float(startTime),
                        "end": float(endTime),
                        "word": wordForFinalDict,
                        "transIndexList": transIndiciesUsed,
                        "wordIndex":wordIndex}) # note the index in the transcipt we record is there word starts, but it may cover several indicies

            # do a check to see if the context of newly added thing is correct, and if not, it may well be a false positive from a transcription error, or similar issue. this requires
            # the word be removed and then added manually as if it was missing instead

            # we need to see if the transScript entries that have been chosen leading up to the new word will actually match up with what they should be, given previous words.
            contextCheckPassed = utils.CheckNewWordContext(wordList, wordIndex, transcriptDict, finalDict, bestFinalDict, transIndiciesUsed)
            userInputNeeded = not contextCheckPassed

        else:
            # the word wasnt' found, user will try ainstead
            userInputNeeded = True
            contextCheckPassed = True # true in that we didn't do one, so don't react as if it occured. name is kinda misleading here but... eah...

        # -----------------------------------------------------------------------------------------------------
        # USER CHOICE
        if userInputNeeded == True:
            
            
            # *** refactor this so a complete choice cycle is a callable function, since we're going them in tandem here? must be a way to do it without a mess
            
            # if word missing/error suspected, we are going to turn what happens next over to the user, as automating the handling of this situation is too vast and error-prone a prospect
            # the user will be shown the word, and given a list of all the transcript entries coming up, with their index numbers. they will be asked to input the correct range of
            # index numbers, with optional inputs to move the window of entries we're looking at, or to declare that a word isn't in teh transcript and can be safely ignored.

            if contextCheckPassed == True:
                print(f"\nDidn't find word [{checkword}] in the transcript. Please indicate which transcript line numbers correspond to this word, if any.")
            else:
                print(f"\nThe word [{checkword}] was found in the transcript but in the incorrect context. " +
                      "Using the provided context, please indicate which transcript line numbers correspond the correct instance of this word, if any.")
            
            uiBall["indexUI"] = previouslySearchedToTransIndex # this is what will 'scroll' our view if the user changes it. this specific choice puts it where the 'readhead' is
                                                                    # which may suck if an error caused it to jump ahead, like our classic 'alfaw' testing example.
            # take user input for what to do next
            newTransIndex = -1
            newTransIndex = userInterface.ProcessUserInput(checkword, uiBall) # what we do, and the updates needed to finalDict, are all handled in here. it has its own loop to keep the
            # script in there until something saficatory is acheived
            
            # the user input may have caused an update to finalDict, which means are 'readhead' moves now to look from that point
            if newTransIndex>-1: # IF THE USER INPUT CHANGES SOMETTHING IE THEY DIDN@T CANCEL / SKIP THE WORD 
                previouslySearchedToTransIndex = newTransIndex
                checkWordFound = True
                print(f"User Input Successful. New trans index: {previouslySearchedToTransIndex}")

                # ----------------------------------------------------------------------------------------
                # POST USER INPUT TROUBLEMAKER SCAN - THIS CAN SERIOUSLY EFFECT THE CONTINUATION OF THE MAIN LOOP!
                # after a user input, we can go through our final dict and see if any words places in earlier were from a lower trans index (ie. they were supposed to appear later in the search).
                # these are the mythical TROUBLEMAKERS, where a script word was transcribed wrong, but correctly later on, or mistakenly transcribed from another word later on.
                # in these cases, we ask teh user to manually locate the trouble maker, then roll the wordIndex back there, strip our finalDict down, and restart our process from the next
                # word. this should get everything back on teh right track, and we can repeat this if it happens again.
                troublemakerFound, troublemakerIndex = utils.CheckFinalDictForTroublemakers(previouslySearchedToTransIndex, finalDict)

                if troublemakerFound == True:
                    x = finalDict[troublemakerIndex]
                    print(f"\nWarning: A word, [{x['word']}] previously found in the transcript may have been taken from the wrong context, or been mistaken for another word." 
                          " Please confirm the correct instance of it.")
                    
                    # we can guess that if the word BEFORE the trouble maker was right, then the real thing the troublemaker was supposed to detect is near that
                    if troublemakerIndex>0:
                        uiBall["indexUI"] = finalDict[troublemakerIndex-1]["transIndexList"][0]
                    else:
                        uiBall["indexUI"] = troublemakerIndex

                    # now we cut everything from the troublemaker onwwards out of the finalDict list, reset the wordIndex to pretend we're looking for that one again, then head back
                    # to teh user interface to look for the replacement
                    wordIndex = x["wordIndex"] # we will then nartuarlly cycle on from here at the end of current wordIndex loop, and it will all be smooth sailing. :D :D :D :D ;D
                    uiBall["wordIndex"] = wordIndex
                    del finalDict[troublemakerIndex:]  # nifty python way of clipping the list

                    #print(finalDict) # testing
                    ## testing, just wanna see the context readouts after our deletion
                    #a, b = utils.CheckNewWordContext(wordList, wordIndex, transcriptDict, finalDict, bestFinalDict, finalDict[-1]["transIndexList"])
                    
                    # USER INPUT
                    newTransIndex = userInterface.ProcessUserInput(wordList[wordIndex], uiBall) # this should sort things out, if the user can be trusted LOL

                    if newTransIndex>-1: # IF THE USER INPUT CHANGES SOMETTHING IE THEY DIDN@T CANCEL / SKIP THE WORD 
                        previouslySearchedToTransIndex = newTransIndex

                # ----------------------------------------------------------------------------------------
                
        # -----------------------------------------------------------------------------------------------------
        # ==========================================================================================================================

        # ------------------------------------------------------------------------------------------
        # here we are are the end of the loop for a given word from the wordList (the script)
        wordIndex = wordIndex-1
        # -------------------------------------------------------------------------------------------------

    # ------------------------------------------------------
    # REVIEW RESULT AND PREPARE FOR NEXT PASS
    # here, we have completed our loop over all the words. it's time to review what we have and decide where to place the new startWordIndex for our next pass.
    # the key

    # By now, we have our finalDict, a list of dictionaries that contain all the correct start and end times in reverse order, plus another dicinotary with only the estimated
    # end tines of words that were in the script but weren't found (often names or things the transcripts will likely get wrong)

    if debugMode == True:
        print("Final Dictionary List:")
        print(finalDict) # for testing
        if len(missingDict)>0:
            print ("Missing Dict List:") # under the new user-input system, this should basically always be enpty
            print (missingDict)


    # ---------------------------------------------------
    # MISSINGDICT ENTRY START TIME GUESS AND MERGE INTO FINALDICT

    # THIS IS DEPRECIATED BUT I WILL LET IT TRY TO AND DO IT ANYWHERE FOR EMERGENCIES
    
    if len(missingDict)>0:
        # we need to slip all the missing dictionary entries into the final one, assigning relevant start times
        # so we find the entry in the finalDict that has the startTime matching the missingDict endTime, and then take the finalDict endTime from the entry 1 index earlier
        # to keep things all in the order we intended to output them in, we'll do a list insert on finalDict (remembering that finalDict is actually a list of dicts, lolololol)
        finalDict = utils.MergeMissingDictIntoFinalDict(finalDict, missingDict)

    # ---------------------------------------------------
    # CHECK SIMILARITY WITH SCRIPT
    
    # AGAIN THIS IS DEPRECEITED, AND IS THE USER INPUT WAS CORRECT IT SHOULDN'T DETECTA NY ISSUES - BUT THAT IS A BIG IF, SO SAFER TO KEEP THIS ACTIVE FOR NOW
    
    # to determine where, if anyway, the earliest word is that messed up teh process. what we would expect to see is that the final dict matches the word list up to a point,
    # then starts being all messed up, probably because of some transcription error where we need to place a word into our finalDict even if it doesn't match in order to overcome
    # the issue. so we'll need to use a sort of quality score where we look at how many error lie ahead of each index, and find a sort of precipise where things seem to go wrong.
    # this will most likey to representing by a long period of mismatches, whereas things like a strange name being different in the transcript will only provide a miss or two, then
    # got back to hits again (if the missing merge thing above has done its job at handing those cases). so, we shall have some threshold number of errors that triggers the end of our
    # check and sets the beginning point for a new pass by placing the error chain origin word into the finalDict artificially (same as the missingDict merge logic), then starting the
    # new pass from the NEXT index. in my head, this will achieve the overcoming of various transcription error possibilities, so let's find out
    finalDict, startWordIndex = utils.ShaveFinalDictToConfirmedMatches(finalDict, wordList, bestFinalDict)
    # ---------------------------------------------------

    # END OF PASS

    # conclude the data gathering by printing out the script (no punctuation unfortunately) according to finalDict
    bestFinalDict.extend(finalDict) # copy our data from the pass into the ultimate result variable. note that lots of it may have been cut out by the above script comparison

    # after the user input update, this should be the end, as we usually only want 1 pass. but a lot can go wrong, so the ability to pass again remains; we shall see how the
    # old automatic error correction attempts and the new user-based ones interact. positively, I expect :D ;D :D ;D ;D ;D ;D ha hahahahahahahahahaha ***

    # now some handy output for reference
    if(debugMode==True):
        print(f"Pass complete. New StartWordIndex = {startWordIndex} (-1 = all passes complete). New final transcript estimation:")
        utils.PrintScriptEstimationFromDict(bestFinalDict)
    # code will now proceed to next pass, if startWordIndex was placed somewhere
    # ---------------------------------------------------

# END OF MAIN LOOP
# lets see the resulting script
if(debugMode==False):
    utils.PrintScriptEstimationFromDict(bestFinalDict)

utils.PrintActualScript(wordList)

# lets see how similar out bestFinalDict and worldList ended up being. - prints the leventshein similarity as a % (which mean similarity based on how many changes are needed to get from one to the other)
utils.CompareBestFinalDictToActualScript(bestFinalDict, wordList)

# =========================================================================================================
# INTERMISSION

# ----------------------------------------------------------------
# SAFETY MARGINS
# in my experience, the transcribing process usually puts the timestamps for a word slightly after the sound of it actually begins, which will cause the start of words to be
# not marked propery as part of the correct audio. as a simple solution to this, i will move all start times forward by a certain safety margin, so that a little more of the
# recording is considered correct.
safetyMarginAmount= 0.15 # in seconds # *** these variables needs to be exposed to user editing in the UI-ified version of this program
endSafetyMarginAmount = 0.02 # i want to bring in the end of each line slightly as well, due to observed inaccuracies
for x in bestFinalDict:
    x["start"] = x["start"] - safetyMarginAmount
    if x["start"] < 0: # lower bound for more safety, this is almost impossible to trigger in practice but if some editing has been done already, the first syllable might be right at the start of the file
        x["start"] = 0
    x["end"] = x["end"] - endSafetyMarginAmount
    if x["end"] < 0: # even more impossible that the last check, but you never know
        x["end"] = 0

# *** we could look for tiny gaps between starta nd end of each entry, and adjust bounds so that the gap is filled, to make auto-editing more smooth by keeping natural gaps
# where possible, since the transcription process sometimes doesn't do this itself
        
# --------------------------------------------------------------
# OUTPUT TRANSCRIPT FILE
# it may be useful to output our finalDict in the same format as the original transcript, so that it can be imported back to audacity as a label file
# this will allow manual editing by marking allth eparts this script THINKS are the correct ones. this might slightoy speed up an editing pass done by a human,
# and means we dont' commit to the potentiall destructive, error-hiding method of just deleting all the wrong parts and hoping the editor notices any problems that arose.

bestFinalDict.reverse()

newTransPath = outputFolder / "Aligned Transcript.txt"
utils.SaveNewTranscript(newTransPath, bestFinalDict) # try-except for this happens in the function

# -----------------------------------------------------------------

# that's the end of our word processing. And the end of part 1 of the script. From here, Part 2 is able to auto edit the file using our new transcript
# HOWEVER at time of writing, audacity can also basically do this automatically, so we'll hold off on that for now.
# =====================================================================================================
