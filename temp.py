# storage zone

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

 ## ============================================



# TIME JUMP CHECKS AFTER USER INPUT GIVES A CONFIRMED NON-ERROR ENTRY
                # after a user input is made, this is a great time to scan the finalDict and see if there are any time jump issues, since we know we have a totally confirmed input,
                # and any prior inputs that actually come later (meaning they have LOWER times because its backwards), are probably erroneous and require further user input
                # this is to defend against a case where a would-be missing word is accidentally found elsehwere in the transcript due to transcription error
                # e.g. the word 'Handy' is transcribed as 'Andy', but the word 'Andy' does appear in the transcript at a totally different place, and will be picked up as an automatically
                # commited word erroneously. We need to go back and do our user choice input for this Handy serach instead to make it right.
               # i'm ta;lk ing about time here, btu i will actually use the transcript index, since thats easier to handle.
               # ALSO VERY IMPORTANT NOTE: it is, in prinipcal, allowed that one part of a recording is intended to overwrite something else that cam earlie (like rerecording a part after
               # a new proninication was discovered). so when there are suspeicious jupms, we don't assume they are wrong and change anything WITHOUT ASKING THE USER. so this block will
               # be more abuot marking suspicious sections and asking the user to either confirm they are okay, and if not, we can go back around and ask them to locate the proper transcript
               # entry

                # keeping in mind that time jump discontinuities are usually caused by the word BEFORE the jump being wrong, what we will do is ask the user to confirm that word in
                # particular

                # we work on a temporoary versino of the most complete possible finalDict, which means using the bestFinalDict from previous passes too (empty on first pass)
                tempDict = bestFinalDict.copy()
                tempDictLen = len(tempDict) # need to store this for future index stuff
                tempDict.extend(finalDict) # now its an estimate of the finished pass output
                i = 0
                iNext = 1

                # we shall scan along the list to find a case where the transIndex goes UP (which means the 'read-head' was moved back by the user).
                # all this really does is render everything before it in the tempDict to be suspect - any word in it could have been an erroneous jump
                # to help identify it, we shall have to show how far along the transcript the readhead jumped in picking that word. while not watertight, this gives a chance
                # to identify very suspicious words. the earliest suspicious word in the dict is the prime candidiate for a manual reselect, then the whole process repeats
                # again from after this newly confirmed point
                susDict = tempDict.copy()
                susDict.clear()
                i = 1
                while i < len(tempDict):
                    if tempDict[i]["transIndex"] > tempDict[i-1]["transIndex"]:
                        susDict.append(tempDict[i-1]) # -1 because i is probably the user-confirmed word, and we want to look before it

                # if nothing sus is found, we will stop here
                if len(susDict) == 0:
                    postUserDebugging = False
                    break
                                                  
                # each entry in susDict represents the suspected occurance of 1 time jump, so we process our reaction to it that many times
                for x in susDict:
                    # we will alert the user,
                    print(f"Potential Transcript Read Error Detected. It is

                    # ***and basically ask them if they want to guess where the problem is - ACTUALLY I THINK THERE IS A WAY TO FIND THE TROUBLEMAKER AUTOMATICALLY
                          # BY MAKING A VERSION OF THE TRANSDICT THAT ONLY HAS TEH USED INDICIES, THEN ESTABLISHING SOME NEARLY CONTENT FOR EACH WORD, AND COMPARING TO
                          # THE WORD LIST

                       
               
            postUserDebugging = False
