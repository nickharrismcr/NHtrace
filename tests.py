'''
Created on 28 Jul 2017

@author: nick
'''

test='''
before 
before
before
public proc ExtrasSearch(    
    companyNo is string,    
    clientNo is large number    
)    
{    
    if clientNo in (0, null) {    
        return      
    }    
    if isInternet and startDate < today + 2 days {    
        raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
        return    
    }    
    dateResultList := empty(dateres.DateResultList)    
    call BldExtraDateBases(companyNo, clientNo)    
    if dateResultList->IsEmpty() {    
        return      
    }    
    let res := empty(result.Result)    
    res->dateList := dateResultList    
    res->extraList := extrares.BuildExtraResult(this)    
    return      


}    
after 
after
after 

'''

test2='''
    
    
--initial comments
--initial comments
--initial comments
--initial comments
--initial comments
--initial comments

public function ExtrasSearch(    
    companyNo is string,    
    clientNo is large number,
    test is date with null,
    test2 is text 
) returns (result.Result with null,boolean,boolean)   
{    
    function innerfunc(
        P_first is string,
        P_second is string
    ) returns boolean
    {
        body := true
        return body 
    }
    
    if clientNo in (0, null) {    
        return null    
    }    
    if isInternet and startDate < today + 2 days {    
        raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
        return null    
    }    
    dateResultList := empty(dateres.DateResultList)    
    call BldExtraDateBases(companyNo, clientNo)    
    if dateResultList->IsEmpty() {    
        return null    
    }    
    let res := empty(result.Result)    
    res->dateList := dateResultList    
    res->extraList := extrares.BuildExtraResult(this)    
    return res    
}    
'''

test3='''     
public function BuildRequest(    
    startDate is date,    
    partyClientNum is large number with null    
) returns Request with null    
{    
    let req := empty(Request)    
    req->company := gl_company_no    
    req->startDate := startDate    
    req->travelDuration := travelDuration    
    req->leaway := leaway    
    req->holidayTypeCode := holidayTypeCode    
    req->product := product    
    req->area := area    
    req->clubStartBase := clubStartBase    
    req->yachtStartBase := yachtStartBase    
    req->yachtEndBase := yachtEndBase    
    req->adultPax := adultPax    
    req->childPax := childPax    
    req->clubCat := clubCat    
    req->clubType := clubType    
    req->yachtCat := yachtCat    
    req->yachtType := yachtType    
    req->sourceValue := sourceVal    
    req->partyClientNo := partyClientNum    
    req->isInternet := false    
    req->coalesceAccom := false    
    req->doPromotions := true    
    req->reqDateRange := empty(baseres.DateRange)    
    req->reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
    req->reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
    return req    
}    
'''

test4='''
    select as tu from accomref,book
    where F_accomref_no=0
    {
    }
    
    update accomref
    where F_accomref_no=0
    {
    }
    '''
    
test5='''
    public procedure    
    RelatedRooms(    
        room is accomres.RoomResult    
    )    
    {    
        if !room->hasRelated {    
            room->hasRelated := true    
            select * from accomrel    
            where F_accom_no = room->accomNo    
            order by F_rel_level    
            {
 
    
                if (doInterconnecting in (AllRooms, NoInterconnecting) or    
                   (doInterconnecting in (InterconnectingOnly, StdPlusInterconnecting) and F_rel_level != 'I')) {    
                    let tu := empty(schema.accom)    
                    quick select as tu from accom index F_accom_no    
                    where accom.F_accom_no = accomrel.F_rel_accom_no    
                    {
                    }
                }
            }
        }
    }
'''
