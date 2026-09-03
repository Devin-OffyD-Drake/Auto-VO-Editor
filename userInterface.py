# =======================================================================================================================================================
# USER INTERFACE

# The user will need to point out where certain unfindable of error-causing words are, indicating this via transcript Dict indicies.
# When a word is not found, the user will be asked to confirm where it is.
# This gives us a definite timestamp we can use to look for earlier time jump errors, and hence raise more questions for the user in order to solve them.
# Since it is important to do this, we must ensure that the final word we search for (the first word in the wordList/script because we search backwards) is always found by the user.
# This will commence a backwards loop looking for erroneous words, and when these time jump errors are found, the overall process has to begin again from the error point.
# Since this may lead to the user having input something several times, we need to either a) inform them well about what is happening or b) store info on their choices to auto implement them later.

# --------------------------------------------------------------------------------------------------------------------------------------------------------
# AID FOR DECIDING WHAT WINDOW OF TRANSCRIPT ENTRIES TO SHOW THE USER WHEN BEGINNING THEIR SEARCH
# We can create a long string that is a concetenation of the whole wordList and whole transDict, allowing us to potentially use a levenstein search based on the word we need to find
#   + a certain number of prior and following characters, to reliably estimate where in the transDict the searched-for word might be. this will likely enhance the manual search process
#   and makeit as smooth as possible.

# *** make objects inn main to store these. we will probably need a dict we can pass back and forth with all the relevant stuff, as this UUI script will interface with lots of things

# ----------------------------------------------------------------------------------------------------------------------------------------------------------
import numpy as np
import utils

# i think this fcuntion was never used, and the keys on the uiBall will be removed
##def CreateContextRefStrings(uiBall):
##    # updates the sstrings which are the full script and full transcript - both things may be changed by certain parts of the code, and hence this should be called to referesh our uiBall
##    scriptString = ""
##    for x in uiBall["wordList"]:
##        scriptString += x
##    transString = ""
##    for x in uiBall["transDict"]:
##        transString += x["word"]
##
##    uiBall["scriptString"] = scriptString
##    uiBall["transString"] = transString


def PrintTranscriptLines(index, uiBall, scrolled = False):
    # formats and prints a console UI for viewing entries in the transciption dict, from a given index on, a given distance onwards, for use in letting the user select given indicies
    # with the optional arg, if this is being called after scrolling our view, we won't show the index marker, because no particular index post-scroll is important

    uiBall["indexUI"] = index # storing this so other things can see it, because i am not using OOP for no reason meaning it can't be a variable on this 'class'
    transDict = uiBall["transDict"]

    showIndexMarker = True # adds something to distguish which index we are building this around, as it may be the one the user is looking for, if this function was fed nicely
    # *** this thing doesn't work when you scroll, need to make sure it only marks something after opening / an automatic search, not after a window scroll

    # transDict display constants
    priorLinesToShow = 60 # size of the window NOTE NOTE NOTE that while i put 'lines' in the names of these, we have changed to a columns models that means this isn't hte line count - this wil be worked out later on
    nextLinesToShow = 60 # we will also show some from before the index, for added chance of finding something amid errors and mishaps
    maxLinesPerCol = 30 # how many lines per column
    maxCols = 4 # how many columns can teh data expand into

    i = index - nextLinesToShow # remember that the 'next' lines in the transcrit are the earlier ones, as the script reads through it backwards
    if i< 0:
        i = 0

    #  i will expand thsi to allow multiple columns in the CLI so more can be displayed at once
    # to do this, i will first gather all the strings to print, then print them seperately. we do this so we can check how long
    # the longest thing we need to print is, as this affects columns width and possibly total count allowed

    # i need to know the string length of the largest possible index in teh transcript. thsi will detemerine how much space is given to numbers
    # in the formating. we can basically do
    iStringWidth = len(str(len(transDict)))
    indexColHeaderLabel = "Index"
    if iStringWidth < len(indexColHeaderLabel): # in theory the header label might need things to be wider
       iStringWidth = len(indexColHeaderLabel)

    # header for columns
    header = f"{'Index':<{iStringWidth}}   Transcript Word"
    headerStrings = []
    for a in range(0,maxCols):
        headerStrings.append(header)

    # line processsing
    lenTD = len(transDict)
    lineStrings = [] # we build an list of all strings to show, then use python's print formating thing below to make it columnate them correctly
    maxColWidthSoFar = 0
    

    # *** need to test the behaviour of this when we're up against the end of the list, we might need to put in dummy entries for what nothing needs to be shown, something like that
    maxTransIndex = index+priorLinesToShow
    while i <= maxTransIndex and i < lenTD and len(lineStrings)<=maxLinesPerCol:
        thisLine = [] # we are making a list of lists, list of lines, where a 'line' i sa list of the strings for each column
        colNo = 0

        while colNo < maxCols: # right the same-line value for colNo columns ahead
            showIndex = i + ((maxLinesPerCol+1) * colNo)
            if showIndex <= maxTransIndex and showIndex < lenTD: # need this apparatus because we are iterating up the whole dict, writing entries that come ahead if there are any
                transWord = transDict[showIndex]["word"]
                
                #  here is what will display for each entry. i want to have the one that is the official ui index be distinct in some way, as often it will be what we're looking for
                if showIndex == index and showIndexMarker == True and scrolled==False:
                    col = f"{showIndex:<{iStringWidth}}***[{transWord}]"
                else:
                    col = f"{showIndex:<{iStringWidth}}   [{transWord}]"
                thisLine.append(col)
                
                if len(col) > maxColWidthSoFar: # storing this so our columsn will hopefully always be wide enough for longest possible thing
                    maxColWidthSoFar = len(col)
            colNo += 1

        lineStrings.append(thisLine)
        i = i + 1

    # ------------------------------------------------------------------------------------------------------
    # THE PRINTING PART

    # col width was dynmicallyl sought after above, but also it needs to be at least the header width
    colWidth = maxColWidthSoFar
    if colWidth < len(header):
        colWidth = len(header)
    colWidth += 3 # we add some padding for neatness

    # now print using the python column width formatting

    # HEADER
    headerOutput = ""
    dividingLine = ""
    for i in range(0,colWidth * maxCols):
        dividingLine += "-"
    
    for s in headerStrings:
        headerOutput += f"{s:<{colWidth}}"
    print(headerOutput)
    print(dividingLine)

    # DATA ROWS
    for row in lineStrings:
        dataOutput = ""
        for s in row: # each row contains each column in order, so this is nice and neat to print out, if this python column formatting will do the work for us
            dataOutput += f"{s:<{colWidth}}" # the > makes it left align the columns
        print(dataOutput)

    if showIndexMarker == True and scrolled==False: # info regarding the index marker idea. might remove if its very often incorrect, we shall see.
        print("*** = Current Transcript Search Position")
    print(dividingLine) # just for formating / ease of display


def ProcessUserInput(wordSearchedFor, uiBall):
    # this si where we will decide what happens when the user inputs a given thing

    inputComplete = False
    newTransIndex = -1

    # testing
    #print(f"Beginning User Input Processing. UI Index: {uiBall['indexUI']}")

    # get the UI up to begin with
    PrintTranscriptLines(uiBall["indexUI"], uiBall)


    while inputComplete == False:
        print("Nearby Context Words In Script: " + GetSearchedWordContext(uiBall["wordList"], uiBall["wordIndex"]))
        print()
        uInput = input(f"Select the rows numbers corresponding to [{wordSearchedFor}] (single number, or a range formated as X-Y).\n" +
                       "If you can't see it, type 'search' to try to find it automatically. Type 'help' for a full list of commands.\n")

        uInput = uInput.strip()

        # now we'll see what we got. we handle the allowed things, and refuse to continue unless something valid was given

        # is it a single number?
        if uInput.isdigit():
            intInput = int(uInput)
            # we are saying that the looking for word is entirely covered by this one transDict index. we can add it to the final dict and move right on
            startTime = uiBall["transDict"][intInput]["start"]
            endTime = uiBall["transDict"][intInput]["end"]

            # upda the transcript to be correct thing - this will help with future checks, passes, and general neatness
            uiBall["transDict"][intInput]["word"] = wordSearchedFor
            
            uiBall["finalDict"].append({"start":startTime, "end":endTime,"word":wordSearchedFor, "transIndexList":[intInput], "wordIndex":uiBall["wordIndex"]})
            print("New Final Dict Entry created by user input: " + str(uiBall["finalDict"][-1]))

            newTransIndex = intInput
            inputComplete = True

        # is it a range?
        elif "-" in uInput: # range input attempted - we will do a slightly different version of the above finalDict appending, sorry about the reptiation
            parts = uInput.split("-")
            if len(parts) == 2: # 2 numbers, that's a good sign, try to parse them
                try:
                    startIndex = int(parts[0])
                    endIndex = int(parts[1])
                
                    # with our 2 indicies, we can get the times for the word from the transDict to put in our finalDict
                    startTime = uiBall["transDict"][startIndex]["start"]
                    endTime = uiBall["transDict"][endIndex]["end"]

                    # ------------------------------------------------------------------------
                    # TRANSCRRIPT MANIPULATION TO MAKE UPDATE EASIER
                    # update to the transcript is a little harder here. we we essentially do is take the start an dend time and overrite endIndex with everything, so it gets
                    # condensed to one transcript entry from now on. then we empty the other entries used here just easier than trying to work out hwo to spread the word out, obvs.
                    x = uiBall["transDict"][endIndex]
                    x["start"] = startTime
                    x["end"] = endTime
                    x["word"] = wordSearchedFor
                    #transIndexList key-value should already be set correct, its just its own index
                    x["wordIndex"] = uiBall["wordIndex"]

                    # now we just make the word "" for the other transDict entries involved, which will effectively ignore them, without any messing around with deletion and index changes
                    i = startIndex
                    while i < endIndex: # ignoreing the endIndex itself, of course
                        uiBall["transDict"][i]["word"] = ""
                        i += 1
                    # ------------------------------------------------------------------------

                    # now lets commit our findings
                    uiBall["finalDict"].append({
                        "start": float(startTime),
                        "end": float(endTime),
                        "word": wordSearchedFor,
                        "transIndexList":list(range(startIndex, endIndex + 1)),
                        "wordIndex":uiBall["wordIndex"]}) # that listrange thing will make the list contain all th enumbers our start and end indicies imply
                    print("New Final Dict Entry created by user input: " + str(uiBall["finalDict"][-1]))
                    
                    newTransIndex = startIndex # lets us return this to get the main loop going aghain from this confirmed correct point
                    inputComplete = True
                    
                except ValueError:
                    print("Invalid range format.")
            else:
                print("Too many dashes, not a valid range.")

        # is it a seek command? we check this by looking for the word seek as the first characters, then assume the rest will be a single number
        elif "seek" in uInput.lower():
            seekInput = uInput.lower().replace("seek", "").strip()
            if seekInput.isdigit():
                intInput = int(seekInput)
                ScrollTranscriptWindow(False, uiBall, intInput) # first arg doesn't actually matter when this function isused with its optional arg
            else:
                print("Invalid seek command. Format is: seek X, where X is the index number to center the list on.")

        else:
            # its not a number, and doesn' thave -. so lets assume its a written command.
      
            # *** a 'cancel all' mode where it will just take cancel as teh option for all future questions and let you output whatevetr yuo got as the transcript so far
            # once i have 'super guess mode' i will implement this in place of cancel-all
            match uInput:

                case "next" | "n":
                    ScrollTranscriptWindow(True, uiBall) # no inputComplete=true because we just repeat the input request at the new position

                case "prev" | "p":
                    ScrollTranscriptWindow(False, uiBall)

                case "start" | "s":
                    ScrollTranscriptWindow(False, uiBall, 0)

                case "end" | "e":
                    ScrollTranscriptWindow(False, uiBall, len(uiBall["transDict"])-1)

                case "cancel" | "c":
                    # this menas we just want to give up on the word and not include it in the final dict.
                    # i think we can just do nothing, as the calling code will carry on assuming the matter was resolved and start looking for the next word
                    # actually to make sure we ignore this word for sure, we shall ""-ifiy it in the wordList
                    uiBall["wordList"][uiBall["wordIndex"]] = ""
                    inputComplete = True

                case "search" | "?": # tries to guess where the current word is from prior transcript entries and a fussy matching method
                    searchedIndex = EstimateTransIndexForAWordFromContext(uiBall)
                    ScrollTranscriptWindow(False, uiBall, searchedIndex)

                case "help" | "h": # prints out some info on all the commands that are allowed
                       print(f"Options for interacting with the transcript search process:\n" +
                             "1) Enter an Index number to indicate it corresponds to the searched-for word.\n"
                             +"2) Enter a range of Index numbers like 100-105 if the searched-for word covers a range.\n"
                             +"3) Enter 'next' or 'prev' to scroll the selection of transcript rows.\n"
                            +"4) Enter 'search' to have the program try to find the word via a rough match (warning: may indicate the wrong word, check carefully).\n"
                       +f" Type 'cancel' to not include [{wordSearchedFor}] in the finished output.\n")

                case _:
                     # not valid, the loop will go around again
                    print("Your input was invalid. Make sure it exactly matches one of the options offered.\n")

    # ---------------------------------
    # CONCLUDE AND RETURN
    if newTransIndex>-1:
        uiBall["indexUI"] = newTransIndex

    return newTransIndex # returns as -1 if none was set
           

def ScrollTranscriptWindow(forwards, uiBall, scrollToIndex = -1):
    # shows the next range for the transcript window. make forwards = false to change the directino of movement
    # optioan arg lets you scroll to a given place instead

    scrolled = False
    if scrollToIndex == -1:
        windowSlideDistance = 100 # its probably a good idea to have this be lower than the window size defined in the ui printing function
        scrolled = True
        
        newIndex = uiBall["indexUI"]
        if forwards == True:
            newIndex = newIndex + windowSlideDistance
        else:
            newIndex = newIndex - windowSlideDistance
    else:
        newIndex = scrollToIndex

    # validate / clamp range
    newIndex = np.clip(newIndex,0,len(uiBall["transDict"])-1)

    PrintTranscriptLines(newIndex, uiBall, scrolled) # uiBall index will be set right away in here

def GetSearchedWordContext(wordList, wordIndex):
    # when asking the user for a specific word, it's easier to give them a load of words around it in the list as context

    contextWindow = 6 # this many words before and after will be provided - you actually get this - 1 because 1 spot is used by the orignal word

    context = f"[{wordList[wordIndex]}]"

    # backward context
    i = 1 # 1 starst at 1 since we dont' need the original word, ie. the i = 0 case
    while wordIndex - i > wordIndex - contextWindow and wordIndex - i >= 0:
        context = wordList[wordIndex-i] + " " + context
        i = i +1

    # forward context
    i = 1
    while wordIndex + i < wordIndex + contextWindow and wordIndex + i < len(wordList):
        context = context + " " + wordList[wordIndex+i]
        i = i +1

    return context

def EstimateTransIndexForAWordFromContext(uiBall):
    # we will try to guess where in the transindex the currently searched for word is, by looking at the script characters that come AFTER it,
    # and trying to match them to a series of transDict characters starting from each index. the match does not need to be exact, and we can search the whole transcript in principcal
    # the idea is the real position will likely contain something that at least vaguely looks like the real script, if the window is large enough, whereas any other point will only
    # be able to resmeble it by accident. if the script contains repeating setnences deliberately, then may god have mercy on our souls.
    # to decide our output, i will get a levenshein score for how good our comparison looks from each index, then return the best one, with honourable mentions to
    # other higher scorers (printed out so the user can seek those to check as well if needed)

    # all the transDict entries that are confirmed so far. these should representing everything that comes after the searched-for word
    #tempTransDict = utils.GetConfirmedTransDictList(uiBall["transDict"], uiBall["finalDict"], uiBall["bestFinalDict"])
    tempTransDict = uiBall["transDict"].copy()

    # how many characters to make our comparison with. needs to be big enough to avoid accidental matches, small enough to avoid the fact teh transcript can
    # contain arbitrarily large amounts of non-script content which will muddy our comparison
    contextWindow = 20 # no logic behind this chosen value, just guessing

    # -----------------------------------------------
    # PREPARE SCRIPT CONTEXT STRING FOR COMPARISON
    scriptContext = ""
    i = 1 # start the below loop at i = 1 as we will compare with everything after the search word, NOT including it, as our confirmed transDict list doesn't have it yet, obvs. we are comparing only adjacent data.
    wl = uiBall["wordList"]
    wIndex = uiBall["wordIndex"]
    while len(scriptContext) < contextWindow and wIndex + i < len(wl):
        scriptContext += wl[wIndex + i].strip()
        i += 1
    if len(scriptContext) > contextWindow:
        scriptContext = scriptContext[0:contextWindow-1] # now we have the right number of characters
        
    contextWindow = len(scriptContext) # we need this because if we're up against teh end of the word list and have too few charcters, we'll just have to do this job with a lesser context window
    #print(f"Searching for previously matched transcript positions that most match script context: {scriptContext}")
    # ------------------------------------------------
    # MAIN SEARCH LOOP

    indexScores = [] # i will make a list of dicts that have the index from the transcript, and the score. we will utilmately just score by score and have our candidates
    i = 0

    # WHERE TO START
    # we don't really need to loop the whole thing. while that's teh safest method, we could take the shortcut of assuming that we will be earlier thanthe lowest index used in the final
    # dict - unfortuantely we don't have access to previousTransIndexSearchedTo. Or do we...? - update: no.
    lowestIndex = len(tempTransDict)-1 # super caveman way of finding this because i have no vibecoding right now wwaahh
    for x in uiBall["finalDict"]:
        ti = x["transIndexList"][0]
        if ti < lowestIndex:
            lowestIndex = ti
    
    print(f"Searching for [{wl[wIndex]}] via its intended script context. This might take a moment for long transcripts.")
    while i + contextWindow < len(tempTransDict): # we'll stop bothering to search as we get the 'front' of our search area to the end, to avoid conplication with the window being mismatched in size

        transContext = ""
        j = 0
        # loop over the next [contextWindow] entries, building our string
        while len(transContext) < contextWindow and i + j < len(tempTransDict):
            transContext += tempTransDict[i + j]["word"]
            j += 1
        transContext = transContext[0:contextWindow] # trim to right size as we probably went over

        # now let's make our comparison
        score = utils.GetLevensteinDistance(scriptContext, transContext)
        indexScores.append({"index":tempTransDict[i]["transIndexList"][0],"score":score, "context":transContext})

        i += 1

    #print(indexScores) # testing

    # ------------------------------------------------------
    # PROCESS RESULTS
    # by now, we have a list of the all the scores we've found. their index in their own list will be the same as the matching transIndex.
    # here is a coppilot python-fu method to get a list of the 5 best indicies from the score list without actually sorting the list, hopefully.
    topCount = 5
    if topCount > len(indexScores):
        topCount = len(indexScores)
    if topCount > 0:
        indexScores.sort(key=lambda d: d["score"], reverse=True) # makes our dict have the best scores at hte top. now lets take our pick.
        bestString = ""
        for i in range(0,topCount):
            bestString += f"[{str(indexScores[i]['index'])}] "
        print(f"Best suspected locations of [{wl[wIndex]}] are: {bestString}")

        # we shall return teh best one, potentially to jump there automatically
        return indexScores[0]['index'] -1 # i will add -1 because in practice it is going to be the entry 1 step earlier that where the best match is (assuming best match is the actual words said withotu mistakes inteh run up to the word in question)
    else:
        print(f"Search for word [{wl[wIndex]}] has failed. Sorry.")
        return -1
    

def DrawProgressBar(wordList, wordIndex):
    # prints something tp represent a progress bar, based on how far through teh world list we are (going backwards)

    totalCount = len(wordList)
    currentCount = totalCount - wordIndex
    percent = (currentCount / totalCount) * 100

    msg = ""
    for i in range(1,100): # we will make a little ascii progress bar type thing
        if i <= percent:
            msg += "O"
        else:
            msg += "-"


    print(msg + f" {int(percent)}%")
