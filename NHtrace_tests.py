req='''constant numberOfCompanies = 5    
    
public type InterconnectingSearch is number    
public constant AllRooms = 0    
public constant InterconnectingOnly = 1    
public constant NoInterconnecting = 2    
public constant StdPlusInterconnecting = 3    
    
public type PriceRange is number    
public constant PriceRange1000 = 1    
public constant PriceRange2000 = 2    
public constant PriceRange3000 = 3    
public constant MaxPriceRange = 3 -- used for range checking    
    
public class RestrictedAccomList is public linkedlist.List    
{

    
    fullList is boolean    
}
    
    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
-------Request class def starts here ---------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
    
public class Request is    
{

    
    description is string    
    company is string    
    startDate is date    
    travelTime is fixed prec 2    
    travelDuration is number    
    leaway is number    
    holidayTypeCode is number    
    product is string    
    area is string    
    clubStartBase is string with null    
    yachtStartBase is string with null    
    yachtEndBase is string with null    
     showAnyYachtEndBase is boolean with null     
    adultPax is number    
    childPax is number    
    infantPax is number    
    clubCat is number    
    clubType is string    
    yachtCat is number    
    yachtType is string    
    yachtAccomNo is large number
    isInternet is boolean    
    price is PriceRange    
    partyClientNo is large number with null    
    sourceValue is string    
    noType is basket.BasketNumberType    
    searchNo is large number    
    yachtExtraType is string with null    
    coalesceAccom is boolean    
    doPromotions is boolean    
    baseTravelDur is number    
    reqDateRange is baseres.DateRange    
    showHeldBookings is boolean    
    showAvailableBases is boolean    
    restrictedBases is linkedlist.List with null    
    restrictedBasesHash is schash.Hash with null    
    checkExpectedPax is boolean with null -- variable to check if the expected pax of boat falls within range for leboat only    
    extrasRequired is boolean with null
    
    private minYachtStatus is accomres.Status with null    
    private minClubStatus is accomres.Status with null    
    private checkValid is boolean -- If set remove invalid dates from output    
    
    private resultCount is number    
    private doInterconnecting is InterconnectingSearch with null    
    private doPartial is boolean    
    --private    
    clubProduct is string    
    yachtProduct is string    
    holidayType is holtype.HolidayType    
    private flightProduct is string    
    private package is string    
    
    extraOptions is extrareq.ExtrasRequest with null    
    flightRequests is flightreq.FlightsRequest with null    
    accomRequests is accomreq.Accommodation with null    
    clubBases is baseres.BaseDatesList with null    
    yachtBases is baseres.BaseDatesList with null    
    dateResultList is dateres.DateResultList with null    
    promotionResultList is promores.PromotionDateResultList with null    
    closedBaseList is baseres.ClosedBaseList with null    
    baseLinkList is baseres.BaseLinkList with null    
    
        
    --------------------------------------------------------------------------------------------------------------------------    
    proc PopulateFromXML(inNode is xmlnodes.BaseNode)    
    {
    
        holidayTypeCode := inNode->FindNumberElement("holiday_type")    
        company := gl_company_no    
        startDate := inNode->FindDateElement("travel_date")    
        travelDuration := inNode->FindNumberElement("duration")    
        leaway := inNode->FindNumberElement("leeway", 0)    
        reqDateRange := empty(baseres.DateRange)    
        reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
        reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
        product := inNode->FindStringElement("product", "")    
        area := inNode->FindStringElement("area", "")    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
    
             holidayType := F_holiday_type    
        }
    
        clubStartBase := ""    
        yachtStartBase := ""    
        yachtEndBase := ""    
        let centreList := inNode->FindElement("centre_list") with null    
        if centreList != null    
        {    
            let centre := centreList->FindElement("centre") with null    
            let firstStartBase := centre->FindStringElement("start_base")    
            let cachedBase := cache.GetBase(gl_company_no, firstStartBase)    
                with null    
            if cachedBase = null    
            {    
                raise ex.arg, "Unrecognised base code " ^ firstStartBase    
            }    
            product := cachedBase->F_product    
            area := cachedBase->F_area    
    
            case holidayType {    
            value holtype.Club    
                clubStartBase := firstStartBase    
            value holtype.Yacht, holtype.Waterways    
                yachtStartBase := firstStartBase    
                yachtEndBase := centre->FindStringElement("end_base", "")    
            value holtype.ClubYacht    
                clubStartBase := firstStartBase    
                centre := centre->GetNext()    
                if centre = null    
                {    
                    yachtStartBase := ""    
                    yachtEndBase := ""    
    
                }    
                else    
                {    
                    yachtStartBase := centre->FindStringElement("start_base")    
                    yachtEndBase := centre->FindStringElement("end_base", "")    
                }    
    
            value holtype.YachtClub    
                yachtStartBase := firstStartBase    
                yachtEndBase := centre->FindStringElement("end_base", "")    
                centre := centre->GetNext()    
                if centre = null    
                {    
                    clubStartBase := ""    
    
                }    
                else    
                {    
                    clubStartBase := centre->FindStringElement("start_base")    
                }    
    
            otherwise    
                raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
            }    
        }    
        adultPax := inNode->FindNumberElement("adult_pax", 0)    
        childPax := inNode->FindNumberElement("child_pax", 0)    
        infantPax := inNode->FindNumberElement("infant_pax", 0)    
    
        if adultPax + childPax = 0    
        {    
            raise ex.arg, "Incorrect pax specified.  Either adultPax or childPax must be greater than 0"    
        }    
    
        clubCat := inNode->FindNumberElement("club_accom_cat", 0)    
        yachtCat := inNode->FindNumberElement("yacht_accom_cat", 0)    
        clubType := inNode->FindStringElement("club_accommodation_type", "")    
        yachtType := inNode->FindStringElement("boat_accommodation_type", "")    
        yachtAccomNo := inNode->FindNumberElement("boat_accommodation_id",0)    
        isInternet := true    
        doPromotions := true    
        coalesceAccom := true    

        extrasRequired := inNode->FindBooleanElement("extras_reqd", true)
    
        let interconnectingReqd :=    
            inNode->FindBooleanElement("interconnecting_reqd", true)    
    
        if interconnectingReqd    
        {    
            if accomRequests = null    
            {    
                accomRequests := empty(accomreq.Accommodation)    
            }    
            if accomRequests->clubRequest = null    
            {    
                accomRequests->clubRequest := empty(accomreq.ClubRequest)    
            }    
            accomRequests->clubRequest->interconnecting := true    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := (StdPlusInterconnecting if accomRequests->clubRequest->interconnecting, NoInterconnecting otherwise)    
            }    
        } else {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := NoInterconnecting    
            }    
        }    
    
        let flightsReqd :=    
            inNode->FindBooleanElement("flights_reqd", false)    
    
        baseTu is schema.base with null    
        case holidayType {    
        value holtype.Club, holtype.ClubYacht    
            if clubStartBase != "" {    
                baseTu := cache.GetBase(gl_company_no, clubStartBase)    
            }    
        value holtype.Yacht, holtype.Waterways, holtype.YachtClub    
            if yachtStartBase != "" {    
                baseTu := cache.GetBase(gl_company_no, yachtStartBase)    
            }    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        if flightsReqd or (baseTu != null and (company = "1" or company = "7") and gl_inv_co = "1" and !pub.CanExFlights(baseTu->F_base_code, isInternet))    
        {    
            if flightRequests = null    
            {    
                flightRequests := empty(flightreq.FlightsRequest)    
            }    
            flightRequests->required := true    
            flightRequests->findPartial := false    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
        -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    
        -- If this is IWW, then search for all bases, one ways and round trips.    
        if company in ("4", "5") {    
            showAvailableBases := true    
        }    
    }
    
        
    --------------------------------------------------------------------------------------------------------------------------    
    proc PopulateFromBookXML(    
        inNode is bsbook.In,    
        adltsPax is number,    
        kidsPax is number,    
        infPax is number    
    )    
    {
    
        company := gl_company_no    
        startDate := inNode->holDet->startDate    
        travelDuration := inNode->holDet->holDuration    
        leaway := 0    
        reqDateRange := empty(baseres.DateRange)    
        reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
        reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
        adultPax := adltsPax    
        childPax := kidsPax    
        infantPax := infPax    
        if inNode->boatDet != null {    
            yachtStartBase := inNode->boatDet->startBase    
            yachtEndBase := (inNode->boatDet->startBase if inNode->boatDet->endBase in (null, ""), inNode->boatDet->endBase otherwise)    
            yachtType := inNode->boatDet->accomType    
            yachtAccomNo := inNode->boatDet->accomNo
        }    
        if inNode->roomDet != null {    
            clubStartBase := inNode->roomDet->base    
            clubType := inNode->roomDet->accomType    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
        -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    }
    
        
    --------------------------------------------------------------------------------------------------------------------------    
    proc PopulateFromAccomref (    
        accRefTu is schema.accomref,    
        adltsPax is number,    
        kidsPax is number,    
        infPax is number    
    )    
    {
    
        company := gl_company_no    
        startDate := accRefTu->F_start_date    
        travelDuration := accRefTu->F_duration    
        leaway := 0    
        reqDateRange := empty(baseres.DateRange)    
        reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
        reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
        adultPax := adltsPax    
        childPax := kidsPax    
        infantPax := infPax    
            
        if pub.GetYachtRoom(accRefTu->F_accom_no) = "Y"    
        {    
                yachtStartBase := accRefTu->F_base_code    
                yachtEndBase := (accRefTu->F_base_code if accRefTu->F_end_base in (null, ""), accRefTu->F_end_base otherwise)    
                    
                -- if this is IWW and a short break we need to use the short break code    
                if gl_company_no = "5" and travelDuration < 7    
                {    
                        yachtStartBase := "SB" ^ yachtStartBase    
                        yachtEndBase := "SB" ^ yachtEndBase    
                }    
                yachtType := accRefTu->F_acc_type    
            } else {    
                clubStartBase := accRefTu->F_base_code    
                clubType := accRefTu->F_acc_type    
        }    
            
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
         -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    }
    
        
    --------------------------------------------------------------------------------------------------------------------------    
    -- What special offer codes do we need? How are these going to be supported? See ravail.IsOfferType    
    -- What agent information do we need?    
    
    public procedure SetExtraOptions(    
        extras is extrareq.ExtrasRequest    
    )    
    {
    
        extraOptions := extras    
    }
    
    --------------------------------------------------------------------------------------------------------------------------    
    
    public function SingleAccomReqd(yachtRequest is boolean) returns boolean    
    {
    
        singleAccom is boolean := false    
        if yachtRequest {    
            if (accomRequests != null and (accomRequests->yachtRequest != null or     
                accomRequests->waterwaysRequest != null))    
            {    
                if (holidayType = holtype.Waterways)    
                {    
                    if (accomRequests->waterwaysRequest != null) {    
                        singleAccom := accomRequests->waterwaysRequest->singleYachtAccom    
                    }    
                } else {    
                    if (accomRequests->yachtRequest != null) {    
                        singleAccom := accomRequests->yachtRequest->singleYachtAccom    
                    }    
                }    
            }    
        } else {    
            if (accomRequests != null and accomRequests->clubRequest != null) {    
                singleAccom := accomRequests->clubRequest->singleClubAccom    
            }    
        }    
        return singleAccom    
    }
    
    ------------------------------------------------------------------------------------------------------    
    public function SinglesReqd(yachtRequest is boolean) returns boolean    
    {
    
        singlesReqd is boolean := false    
        if yachtRequest {    
            if (accomRequests != null and (accomRequests->yachtRequest != null or     
                accomRequests->waterwaysRequest != null))    
            {    
                if (holidayType = holtype.Waterways)    
                {    
                    if (accomRequests->waterwaysRequest != null) {    
                        singlesReqd := accomRequests->waterwaysRequest->singles    
                    }    
                } else {    
                    if (accomRequests->yachtRequest != null) {    
                        singlesReqd := accomRequests->yachtRequest->singles    
                    }    
                }    
            }    
        } else {    
            if (accomRequests != null and accomRequests->clubRequest != null) {    
                singlesReqd := accomRequests->clubRequest->singles    
            }    
        }    
        return singlesReqd    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public function ExtrasSearch(    
        companyNo is string,    
        clientNo is large number    
    ) returns result.Result with null    
    {
    
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
    
    
    ------------------------------------------------------------------------------------------------------    
    procedure BldExtraDateBases(    
        companyNo is string,    
        clientNo is large number    
    )    
    {
    
        ------------------------------------------------------------------------------------------------------    
        procedure BldExtraBases(    
            dateResult is dateres.DateResult,    
            companyNo is string,    
            clientNo is large number,    
            startDate is date,    
            dur is number    
        )    
        {
    
            select unique baseref.F_client_no, baseref.F_base_code, baseref.F_end_base,    
                baseref.F_start_date, baseref.F_duration    
            from baseref = accomref index F_client_no    
            where baseref.F_client_no = clientNo    
            and !(pub.get_prod(baseref.F_base_code) in ("EXT", "OEXT"))    
            and baseref.F_start_date = startDate    
            and baseref.F_duration = dur    
            {
    
                    let baseResult := empty(baseres.BaseResult)    
                baseResult->companyNo := companyNo    
                baseResult->startBase := baseref.F_base_code    
                baseResult->endBase := baseref.F_end_base    
    
                select unique accomref.F_client_no, accomref.F_base_code,     
                    accomref.F_start_date, accomref.F_duration, accomref.F_accom_no    
                from accomref index F_client_no    
                where accomref.F_client_no = clientNo    
                and accomref.F_base_code = baseref.F_base_code    
                and accomref.F_start_date = baseref.F_start_date    
                and accomref.F_duration = baseref.F_duration    
                {
    
                    if pub.GetYachtRoom(accomref.F_accom_no) = "Y" {    
                        baseResult->baseType := baseres.YachtBase    
                    } else {    
                        baseResult->baseType := baseres.ClubBase    
                    }    
                    ? := dateResult->baseResultList->UniqueAppend(baseResult)    
                    stop    
                }
    
            }
    
        }
    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        select unique dateref.F_client_no, dateref.F_start_date, dateref.F_duration    
        from dateref = accomref index F_client_no    
        where dateref.F_client_no = clientNo    
        order by dateref.F_start_date ascending    
        {
    
            let dateResult := empty(dateres.DateResult)    
            dateResult->startDate := dateref.F_start_date    
            dateResult->travelDuration := avbkdt.DaysToDuration(dateref.F_duration)    
    
            call BldExtraBases(dateResult, companyNo, dateref.F_client_no,     
                dateref.F_start_date, dateref.F_duration)    
    
            if (dateResult->baseResultList != null and !dateResult->baseResultList->IsEmpty())    
            {    
                ? := dateResultList->UniqueAppend(dateResult)    
            }    
        }
    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public func XMLBookSearch(    
        roomDet is bsbook.InRoomDetails with null,    
        boatDet is bsbook.InBoatDetails with null    
    ) returns result.Result with null    
    {
    
        ------------------------------------------------------------------------------------------------------    
        procedure Product(base is string)    
        {
    
            let tu := cache.GetBase(gl_company_no, base) with null    
            if tu = null {    
                raise ex.arg, "Invalid company base combination" ^ gl_company_no ^ " " ^ base    
            }    
            area := tu->F_area    
            product := tu->F_product    
        }
    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
    
        call cache.Clear()    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
            return null    
        }
    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }
    
        case holidayType {    
        value holtype.Club    
            call Product(clubStartBase)    
            -- Nothing to do    
        value holtype.Yacht, holtype.Waterways    
            call Product(yachtStartBase)    
            -- Nothing to do    
        value holtype.ClubYacht    
            travelDuration := 7    
            if boatDet != null    
            {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            } else {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            }    
        value holtype.YachtClub    
            travelDuration := 7    
            if roomDet != null    
            {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            } else {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            }    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        let oldCompanyNo := gl_company_no    
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
                    return res    
                }
    
                return empty(result.Result)    
            }
    
        }    
        dateResultList := empty(dateres.DateResultList)    
        let dateResult := empty(dateres.DateResult) with null    
        dateResult->startDate := startDate    
        dateResult->travelDuration := avbkdt.DaysToDuration(travelDuration)    
        dateResult := dateResultList->UniqueOrder(dateResult)    
        dateResult->isStart := true    
        if clubStartBase in (null, "") {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, yachtStartBase, yachtEndBase, baseres.YachtBase, true, true)    
        } else {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, clubStartBase, clubStartBase, baseres.ClubBase, true, true)    
        }    
        if accomRequests != null and accomRequests->clubRequest != null {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := (StdPlusInterconnecting if accomRequests->clubRequest->interconnecting, NoInterconnecting otherwise)    
            }    
        } else {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := StdPlusInterconnecting    
            }    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
        -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    
        -- We should only be building the accom list for a single base, for either    
        -- boat or club on a single date.    
        case holidayType {    
        value holtype.Club    
            let room := empty(accomres.RoomResult)    
            call BuildClubList(room->BuildRoomFromRoomDetails(roomDet))    
        value holtype.Yacht, holtype.Waterways    
            let yacht := empty(accomres.YachtResult)    
            call BuildYachtList(yacht->BuildYachtFromBoatDetails(boatDet))    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        call dateResultList->SetValid(holidayType)    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
        return res    
    }
    
    ------------------------------------------------------------------------------------------------------    
    public func AccomrefBookSearch(    
        accRefTu is schema.accomref    
    ) returns result.Result with null    
    {
    
        ------------------------------------------------------------------------------------------------------    
        procedure Product(base is string)    
        {
    
            let tu := cache.GetBase(gl_company_no, base) with null    
            if tu = null {    
                raise ex.arg, "Invalid company base combination" ^ gl_company_no ^ " " ^ base    
            }    
            area := tu->F_area    
            product := tu->F_product    
        }
    
    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        call cache.Clear()    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
            return null    
        }
    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }
    
        case holidayType {    
        value holtype.Club    
            call Product(clubStartBase)    
            -- Nothing to do    
        value holtype.Yacht, holtype.Waterways    
            call Product(yachtStartBase)    
            -- Nothing to do    
        value holtype.ClubYacht    
            travelDuration := 7    
            if pub.GetYachtRoom(accRefTu->F_accom_no) = "Y"    
            {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            } else {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            }    
        value holtype.YachtClub    
            travelDuration := 7    
            if pub.GetYachtRoom(accRefTu->F_accom_no) = "R"    
            {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            } else {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            }    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        let oldCompanyNo := gl_company_no    
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
                    return res    
                }
    
                return empty(result.Result)    
            }
    
        }    
        dateResultList := empty(dateres.DateResultList)    
        let dateResult := empty(dateres.DateResult) with null    
        dateResult->startDate := startDate    
        dateResult->travelDuration := avbkdt.DaysToDuration(travelDuration)    
        dateResult := dateResultList->UniqueOrder(dateResult)    
        dateResult->isStart := true    
        if clubStartBase in (null, "") {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, yachtStartBase, yachtEndBase, baseres.YachtBase, true, true)    
        } else {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, clubStartBase, clubStartBase, baseres.ClubBase, true, true)    
        }    
        if accomRequests != null and accomRequests->clubRequest != null {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := (StdPlusInterconnecting if accomRequests->clubRequest->interconnecting, NoInterconnecting otherwise)    
            }    
        } else {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := StdPlusInterconnecting    
            }    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
    
        -- if this is a leboat request we dont want a min status    
        if gl_company_no = "5"    
        {        
            minYachtStatus := null    
        }    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    
        -- We should only be building the accom list for a single base, for either    
        -- boat or club on a single date.    
        case holidayType {    
        value holtype.Club    
            let room := empty(accomres.RoomResult)    
            call BuildClubList(room->BuildRoomFromAccomref(accRefTu))    
        value holtype.Yacht, holtype.Waterways    
            let yacht := empty(accomres.YachtResult)    
            call BuildYachtList(yacht->BuildYachtFromAccomref(accRefTu))    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        call dateResultList->SetValid(holidayType)    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
        return res    
    }
    
    ------------------------------------------------------------------------------------------------------    
    public function FlightSearch()    
    returns result.Result with null    
    {
    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
            return null    
        }
    
        if isInternet and startDate < today + 2 days {    
            raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
            return null    
        }
    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }
    
        let oldCompanyNo := gl_company_no    
        dateResultList := empty(dateres.DateResultList)    
        promotionResultList := empty(promores.PromotionDateResultList)    
        if area = "" {    
            area := "*"    
        }    
        if clubType = "" {    
           clubType := "*"        
        }    
        if yachtType = "" {    
           yachtType := "*"        
        }    
        if clubStartBase = "" {    
            clubStartBase := "*"    
        }    
        if yachtStartBase = "" {    
            yachtStartBase := "*"    
        }    
        call cache.Clear()    
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
                    return res    
                }
 else {    
                    return empty(result.Result)    
                }
    
            }    
        }    
        doInterconnecting := AllRooms    
        doPartial := false    
        if holidayType in (holtype.Club, holtype.ClubYacht) {    
            call Flights(clubBases, baseres.ClubBase)    
        } else {    
            call Flights(yachtBases, baseres.YachtBase)    
        }    
        let flightCnt := 0    
        let tmpDate := dateResultList->head with null    
        while (tmpDate != null) {    
            let dateRes := dateResultList->GetDateResult(tmpDate) with null    
            if dateRes->routeList != null {    
                if dateRes->routeList->elemCount != 0 {    
                    flightCnt := flightCnt + dateRes->routeList->elemCount    
                } else {    
                    dateRes->isValid := false    
                }    
            }    
            dateRes->baseResultList := null    
            dateRes->promotionList := null    
            tmpDate := tmpDate->next    
        }    
        if flightCnt = 0 {    
            gl_company_no := oldCompanyNo    
            return empty(result.Result)    
        }
    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
        return res    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public function AvailSearch()    
    returns result.Result with null    
    {
    
    
        let oldLeeway := leaway    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
            return null    
        }
    
        if isInternet and startDate < today + 2 days {    
            raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
            return null    
        }
    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }
    
        let oldCompanyNo := gl_company_no    
        dateResultList := empty(dateres.DateResultList)    
        promotionResultList := empty(promores.PromotionDateResultList)    
        if area = "" {    
            area := "*"    
        }    
        if clubType = "" {    
           clubType := "*"        
        }    
        if yachtType = "" {    
           yachtType := "*"        
        }    
        if clubStartBase = "" {    
            clubStartBase := "*"    
        }    
        if yachtStartBase = "" {    
            yachtStartBase := "*"    
        }    
        call cache.Clear()    
        call pricecache.Clear()            
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
                    return res    
                }
 else {    
                    raise ex.arg, msg    
                    return empty(result.Result)    
                }
    
            }    
                
        }    
    
        if doInterconnecting = null {    
            if accomRequests != null and accomRequests->clubRequest != null {    
                doInterconnecting := (InterconnectingOnly if accomRequests->clubRequest->interconnecting, AllRooms otherwise)    
            } else {    
                 doInterconnecting := AllRooms    
            }    
        }    
    
           if flightRequests != null {    
            if (flightRequests->findPartial) {    
                doPartial := true    
            }    
            if flightRequests->required {    
                if holidayType in (holtype.Club, holtype.ClubYacht) {    
                    call Flights(clubBases, baseres.ClubBase)    
                } else {    
                    call Flights(yachtBases, baseres.YachtBase)    
                }    
                let flightCnt := 0    
                let tmpDate := dateResultList->head with null    
                while (tmpDate != null) {    
                    let dateRes := dateResultList->GetDateResult(tmpDate) with null    
                    if dateRes->routeList != null {    
                        if dateRes->routeList->elemCount != 0 {    
                            let baseResultList := dateRes->baseResultList    
                            let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                            dateRes->isValid := false    
                            while baseTmp != null and !dateRes->isValid {    
                                let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                dateRes->isValid := baseResult->isValid    
                                baseTmp := baseTmp->next    
                            }    
                            if dateRes->isValid {    
                                flightCnt := flightCnt + dateRes->routeList->elemCount    
                            }    
                        } else {    
                            dateRes->isValid := false    
                        }    
                    }    
                    tmpDate := tmpDate->next    
                }    
                if flightCnt = 0 {    
                    gl_company_no := oldCompanyNo    
                    if closedBaseList != null and !closedBaseList->IsEmpty() {    
                        let res := empty(result.Result)    
                        res->closedBaseList := closedBaseList    
                        return res    
                    }
    
                    return null    
                }
    
                leaway := 0    
            }    
        }    
        case holidayType {    
        value holtype.Club    
            call BuildClubList()    
        value holtype.Yacht, holtype.Waterways    
            call BuildYachtList()    
        value holtype.ClubYacht    
            call BuildClubList()    
            call BuildYachtList()    
        value holtype.YachtClub    
            call BuildYachtList()    
            call BuildClubList()    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
--call promotions.Debug(Display(1))    
        if flightRequests = null or !flightRequests->required {    
            if holidayType in (holtype.Club, holtype.ClubYacht) {    
                call Flights(clubBases, baseres.ClubBase)    
            } else {    
                call Flights(yachtBases, baseres.YachtBase)    
            }    
        }    
        if showHeldBookings {    
            call AddHeldBookings()    
        }    
        if checkValid {    
            call dateResultList->SetValid(holidayType)    
        }    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        if extrasRequired != false
        {
            res->extraList := extrares.BuildExtraResult(this)    
        }
        res->promotionList := promotionResultList    
        if gl_istui
        {
            call promoreq.Promotions(this, res)    
        }
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
        leaway := oldLeeway    
        return res    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public function PrevDates() returns result.Result with null    
    {
    
        closedBaseList := null    
        dateResultList := null    
        promotionResultList := null    
        reqDateRange->startDate := reqDateRange->startDate - 7 days    
        reqDateRange->endDate := reqDateRange->endDate - 7 days    
        let prevRes := WidenSearch() with null    
        if showHeldBookings {    
            call AddHeldBookings()    
        }    
        return prevRes    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public function NextDates() returns result.Result with null    
    {
    
        closedBaseList := null    
        dateResultList := null    
        promotionResultList := null    
        reqDateRange->startDate := reqDateRange->startDate + 7 days    
        reqDateRange->endDate := reqDateRange->endDate + 7 days    
        let nextRes := WidenSearch() with null    
        if showHeldBookings {    
            call AddHeldBookings()    
        }    
        return nextRes    
    }
    
    --------------------------------------------------------------------------------------------------------------------------    
        
    public function WidenSearch()    
    returns result.Result with null    
    {
    
        validBases is boolean := false    
        errMsg is string := ""    
        if holidayType in (holtype.Club, holtype.ClubYacht) {    
            if clubBases = null or clubBases->IsEmpty() {    
                clubBases := null    
                yachtBases := null    
                validBases, errMsg := BuildBases(reqDateRange)    
            } else {    
                validBases, errMsg := RebuildBases(reqDateRange)    
            }    
        }    
        if holidayType in (holtype.Yacht, holtype.YachtClub, holtype.Waterways) {    
            if yachtBases = null or yachtBases->IsEmpty() {    
                yachtBases := null    
                clubBases := null    
                validBases, errMsg := BuildBases(reqDateRange)    
            } else {    
                validBases, errMsg := RebuildBases(reqDateRange)    
            }    
        }            
        if !validBases {    
            if closedBaseList != null and !closedBaseList->IsEmpty() {    
                let res := empty(result.Result)    
                res->closedBaseList := closedBaseList    
                return res    
            }
    
            return null    
        }
    
        let oldCompanyNo := gl_company_no    
        dateResultList := empty(dateres.DateResultList)    
        promotionResultList := empty(promores.PromotionDateResultList)    
           if flightRequests != null {    
            if (flightRequests->findPartial) {    
                doPartial := true    
            }    
            if flightRequests->required {    
                if holidayType in (holtype.Club, holtype.ClubYacht) {    
                    call Flights(clubBases, baseres.ClubBase)    
                } else {    
                    call Flights(yachtBases, baseres.YachtBase)    
                }    
                let flightCnt := 0    
                let tmpDate := dateResultList->head with null    
                while (tmpDate != null) {    
                    let dateRes := dateResultList->GetDateResult(tmpDate) with null    
                    if dateRes->routeList != null {    
                        if dateRes->routeList->elemCount != 0 {    
                            flightCnt := flightCnt + dateRes->routeList->elemCount    
                        } else {    
                            dateRes->isValid := false    
                        }    
                    }    
                    tmpDate := tmpDate->next    
                }    
                if flightCnt = 0 {    
                    gl_company_no := oldCompanyNo    
                    if closedBaseList != null and !closedBaseList->IsEmpty() {    
                        let res := empty(result.Result)    
                        res->closedBaseList := closedBaseList    
                        return res    
                    }
    
                    return empty(result.Result)    
                }
    
                            
            }    
        }    
        case holidayType {    
            value holtype.Club    
                if clubBases = null or !clubBases->ValidAccom() {    
                    call BuildClubList()    
                } else {    
                    call ProcessClubList(clubBases)    
                }    
            value holtype.Yacht, holtype.Waterways    
                if yachtBases = null or !yachtBases->ValidAccom() {    
                    call BuildYachtList()    
                } else {    
                    call ProcessYachtList(yachtBases)    
                }    
            value holtype.ClubYacht    
                if clubBases = null or !clubBases->ValidAccom() {    
                    call BuildClubList()    
                    call BuildYachtList()    
                } else {    
                    call ProcessClubList(clubBases)    
                    call ProcessYachtList(yachtBases)    
                }    
            value holtype.YachtClub    
                if yachtBases = null or !yachtBases->ValidAccom() {    
                    call BuildYachtList()    
                    call BuildClubList()    
                } else {    
                    call ProcessYachtList(yachtBases)    
                    call ProcessClubList(clubBases)    
                }    
            otherwise    
                raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        if flightRequests = null or !flightRequests->required {    
            if holidayType in (holtype.Club, holtype.ClubYacht) {    
                call Flights(clubBases, baseres.ClubBase)    
            } else {    
                call Flights(yachtBases, baseres.YachtBase)    
            }    
        }    
        call dateResultList->SetValid(holidayType)    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        res->extraList := extrares.BuildExtraResult(this)    
        res->promotionList := promotionResultList    
        call promoreq.Promotions(this, res)    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
        return res    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public function AlternativeSearch()    
    returns result.Result with null    
    {
    
        let oldLeeway := leaway    
        let res := AvailSearch() with null    
        if res = null {    
            -- We found nothing, so do the whole search again.    
            if leaway = 0 {    
                leaway := 7    
                reqDateRange->startDate := ((reqDateRange->startDate - leaway days) if leaway >= 1,     
                                reqDateRange->startDate otherwise)    
                reqDateRange->endDate := ((reqDateRange->endDate + leaway days) if leaway >= 1,     
                                reqDateRange->endDate otherwise)    
                if isInternet and reqDateRange->startDate < today + 2 days {    
                    reqDateRange->startDate := today + 2 days    
                }    
                clubBases := null    
                yachtBases := null    
                res := AvailSearch()    
                if res = null or !res->ValidResultSet(this) {    
                    leaway := oldLeeway    
                    if res != null and res->closedBaseList != null and !res->closedBaseList->IsEmpty()    
                    {    
                        return res    
                    }
    
                    return null    
                }
    
            }    
        } else if !res->ValidResultSet(this) {    
            -- We have an accommodation list, so use this again.    
            if leaway = 0 {    
                leaway := 7    
                reqDateRange->startDate := ((reqDateRange->startDate - leaway days) if leaway >= 1,     
                                reqDateRange->startDate otherwise)    
                reqDateRange->endDate := ((reqDateRange->endDate + leaway days) if leaway >= 1,     
                                reqDateRange->endDate otherwise)    
                if isInternet and reqDateRange->startDate < today + 2 days {    
                    reqDateRange->startDate := today + 2 days    
                }    
                res := WidenSearch()    
                if res = null or !res->ValidResultSet(this) {    
                    leaway := oldLeeway    
                    if res != null and res->closedBaseList != null and !res->closedBaseList->IsEmpty()    
                    {    
                        return res    
                    }
    
                    return null    
                }
    
            } else {    
                if res->closedBaseList = null or res->closedBaseList->IsEmpty() {    
                    res := null    
                }    
            }    
        }    
        leaway := oldLeeway    
        call res->SetPrices(null)    
        return res    
    }
    
    --------------------------------------------------------------------------------------------------------------------------    
        -- search criteria used for tui and now leboat web and new avail also    
    public function TuiGSearch(retRoute is boolean with null)    
    returns result.Result with null    
    {
    
        let oldLeeway := leaway    
            
        let msg := ('Checking Expected Pax')    
        call liberrmsg.LogError('avail',msg)    
            
        let res := empty(result.Result) with null    
        checkExpectedPax := true    
        res := AvailSearch()     
            
        --if res is null then check results for max pax values Leboat web only    
            if (res = null or not(res->ValidResultSet(this))) and !gl_istui    
            {    
                    let msg := ('Checking Max Pax')    
            call liberrmsg.LogError('avail',msg)    
                
                checkExpectedPax := false    
                    res := AvailSearch()    
                        
                    if res != null and res->ValidResultSet(this) {    
                call res->SetPrices(null)    
                return res    
            }
    
                
            checkExpectedPax := true    
        }    
            
        if res = null or not(res->ValidResultSet(this)) {    
            -- We found nothing, so do the whole search again. starting from the day    
            -- before the initial start date then moving one day backwards and forwards    
            -- each iteration up to a max of 4 days either side    
    
                        let msg := ('Checking Alternative dates')    
            call liberrmsg.LogError('avail',msg)    
                            
            let goingLeft := true    
            let jump := 0    
            repeat {    
    
                jump := abs(jump) + 1    
                if goingLeft {    
                    jump := jump * -1    
                    goingLeft := false    
                } else {    
                    goingLeft := true    
                }    
    
                reqDateRange->startDate := reqDateRange->startDate + jump days    
                reqDateRange->endDate := reqDateRange->endDate + jump days    
    
                if isInternet and reqDateRange->startDate < today + 2 days {    
                    reqDateRange->startDate := today + 2 days    
                }    
                clubBases := null    
                yachtBases := null    
                    
                let msg := ('Checking Expected Pax')    
                        call liberrmsg.LogError('avail',msg)    
    
                res := AvailSearch()    
                    
                --if res is null then check results for max pax values leboat web only    
                        if (res = null or not(res->ValidResultSet(this))) and !gl_istui    
                        {    
                                checkExpectedPax := false    
                                    
                                let msg := ('Checking Max Pax')    
                            call liberrmsg.LogError('avail',msg)    
                
                                res := AvailSearch()    
                                    
                                if res != null and res->ValidResultSet(this) {    
                            call res->SetPrices(null)    
                            return res    
                        }
    
                            
                        checkExpectedPax := true    
                        }    
    
                if res != null and res->ValidResultSet(this) {    
                    call res->SetPrices(null)    
                    return res    
                }
    
            } until abs(jump) >= 8    
                
            -- if res is still null then set start bases and end bases to the other way round and call the TuiGSearch again    
                    
        }    
        leaway := oldLeeway    
        call res->SetPrices(null)    
        return res    
        
    }
    
    
    --------------------------------------------------------------------------------------------------------------------------    
    procedure ProcessClubList(    
        baseList is baseres.BaseDatesList with null    
    )    
    {
    
        if baseList = null {    
            return    
        }    
        if dateResultList = null or dateResultList->IsEmpty() {    
            let tmpBase := baseList->head with null    
            while (tmpBase != null) {    
                let baseDate := baseList->GetBaseDatesList(tmpBase)     
                let dateRangeList := baseDate->dateRangeList    
                let tmpDate := dateRangeList->head with null    
                while (tmpDate != null) {    
                    let dateRange := dateRangeList->GetDateRange(tmpDate)    
                    let avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                    let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                    let avbkDateRange := empty(avbkdt.DateTimeRange)->Init((dateRange->startDate - leaway days), (dateRange->startDate + leaway days))    
                    gl_company_no := baseDate->companyNo    
                    let roomList := baseDate->roomList with null    
                    let tmpRoom := (roomList->head if roomList != null, null otherwise) with null    
                    while (tmpRoom != null) {    
                        let room := roomList->GetRoomResult(tmpRoom)    
                        call RoomAvailability(null, baseDate->baseCode, baseDate, null, room)    
                        tmpRoom := tmpRoom->next    
                    }    
                    tmpDate := tmpDate->next    
                }    
                tmpBase := tmpBase->next    
            }    
        } else {    
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                if dateRes->isStart and dateRes->isValid {    
                    let baseResultList := dateRes->baseResultList    
                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                    while baseTmp != null {    
                        let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                        if baseResult->isValid {    
                            let tmp := (clubBases->head if clubBases != null, null otherwise) with null    
                            while (tmp != null) {    
                                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                if baseres.BaseResultEqualBaseDate(baseResult, baseDate) or     
                                    holidayType = holtype.YachtClub    
                                {    
                                    gl_company_no := baseDate->companyNo    
                                    let roomList := baseDate->roomList with null    
                                    let tmpRoom := (roomList->head     
                                            if roomList != null,     
                                            null otherwise) with null    
                                    while (tmpRoom != null) {    
                                        let room := roomList->GetRoomResult(    
                                                tmpRoom)    
                                        call RoomAvailability(null,     
                                            baseDate->baseCode,     
                                            baseDate, dateRes, room)    
                                        tmpRoom := tmpRoom->next    
                                    }    
                                }    
                                tmp := tmp->next    
                            }    
                        }    
                        baseTmp := baseTmp->next    
                    }    
                }    
                dateTmp := dateTmp->next    
            }    
        }    
    }
    
    
    --------------------------------------------------------------------------------------------------------------------------    
    procedure ProcessYachtList(    
        baseList is baseres.BaseDatesList with null    
    )    
    {
    
            
        if baseList = null {    
            return    
        }    
        if dateResultList = null or dateResultList->IsEmpty() {    
            let tmpBase := baseList->head with null    
            while (tmpBase != null) {    
                let baseDate := baseList->GetBaseDatesList(tmpBase)     
                let dateRangeList := baseDate->dateRangeList    
                let tmpDate := dateRangeList->head with null    
                while (tmpDate != null) {    
                    let dateRange := dateRangeList->GetDateRange(tmpDate)    
                    let avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                    let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                    let avbkDateRange := empty(avbkdt.DateTimeRange)->Init((dateRange->startDate - leaway days), (dateRange->startDate + leaway days))    
                    gl_company_no := baseDate->companyNo    
                    let yachtList := baseDate->yachtList with null    
                    let tmpYacht := (yachtList->head if yachtList != null, null otherwise) with null    
                    while (tmpYacht != null) {    
                        let yacht := yachtList->GetYachtResult(tmpYacht)    
                        call YachtAvailability(null, baseDate->baseCode, baseDate, null, yacht)    
                        tmpYacht := tmpYacht->next    
                    }    
                    tmpDate := tmpDate->next    
                }    
                tmpBase := tmpBase->next    
            }    
        } else {    
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                if dateRes->isStart and dateRes->isValid {    
                    let baseResultList := dateRes->baseResultList    
                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                    while baseTmp != null {    
                        let baseResult := baseResultList->GetBaseResult(baseTmp)    
                        let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
                        while (tmp != null) {    
                            let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                            if baseres.BaseResultEqualBaseDate(baseResult, baseDate) or     
                                holidayType = holtype.ClubYacht    
                            {    
                                gl_company_no := baseDate->companyNo    
                                let yachtList := baseDate->yachtList with null    
                                let tmpYacht := (yachtList->head     
                                            if yachtList != null,     
                                            null otherwise) with null    
                                while (tmpYacht != null) {    
                                    let yacht := yachtList->GetYachtResult(    
                                            tmpYacht)    
                                    call YachtAvailability(null,     
                                        baseDate->baseCode, baseDate,     
                                        dateRes, yacht)    
                                    tmpYacht := tmpYacht->next    
                                }    
                            }    
                            tmp := tmp->next    
                        }    
                        baseTmp := baseTmp->next    
                    }    
                }    
                dateTmp := dateTmp->next    
            }    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    function CheckBaseClosures(    
        compNo is string,    
        baseType is baseres.BaseType,    
        startBase is string,    
        endBase is string with null,    
        requestRange is baseres.DateRange    
    ) returns baseres.DateRangeList with null    
    {
    
        dateRangeList is baseres.DateRangeList with null    
        dateListCnt is number := 1    
        for i = requestRange->startDate to requestRange->endDate {    
            let useStartBase := true    
            let baseClsd, clsdMsg := pub.BaseClosed(compNo, startBase, i, baseTravelDur)    
            if !baseClsd and startBase != endBase and endBase != null {    
                baseClsd, clsdMsg := pub.BaseClosed(compNo, endBase, (i + baseTravelDur days), 0)    
                useStartBase := false    
            }    
            if baseClsd {    
                if dateRangeList != null and !dateRangeList->IsEmpty() and     
                    (dateListCnt = dateRangeList->elemCount)    
                {    
                    dateListCnt := dateListCnt + 1    
                }    
                -- Append the base closure to the list.    
                if closedBaseList = null {    
                    closedBaseList := empty(baseres.ClosedBaseList)    
                }    
                let closedBase := empty(baseres.ClosedBase)    
                closedBase->companyNo := compNo    
                closedBase->baseCode := (startBase if useStartBase, endBase otherwise)    
                closedBase->closureMsg := clsdMsg    
                closedBase->baseType := (baseType if useStartBase, baseres.YachtBase     
                    if holidayType = holtype.Yacht, baseres.Waterways otherwise)    
                ? := closedBaseList->UniqueAppend(closedBase)    
            } else {    
                if (dateRangeList = null or dateListCnt > dateRangeList->elemCount) {    
                    if dateRangeList = null {    
                        dateRangeList := empty(baseres.DateRangeList)    
                    }    
                    let dateRange := empty(baseres.DateRange)    
                    dateRange->startDate := i    
                    dateRange->endDate := i    
                    ? := dateRangeList->UniqueAppend(dateRange)    
                }    
                if dateListCnt = dateRangeList->elemCount {    
                    let tmpDateRange := cast(dateRangeList->tail, baseres.DateRange) with null    
                    if tmpDateRange != null {    
                        tmpDateRange->endDate := i    
                    }    
                }    
            }    
        }    
        return dateRangeList    
    }
    
    --------------------------------------------------------------------------------------------------------------------------    
    private function RebuildBases(    
        requestRange is baseres.DateRange    
    ) returns (boolean, string)    
    {    
        -- Determine the closed base's type depending on the requested holiday type.    
        baseType is baseres.BaseType    
        case holidayType {    
            value holtype.Club, holtype.ClubYacht    
                baseType := baseres.ClubBase    
            value holtype.Yacht, holtype.YachtClub    
                baseType := baseres.YachtBase    
            value holtype.Waterways    
                baseType := baseres.Waterways    
        }    
        function ProcessBases(    
            reqRange is baseres.DateRange,    
            baseList is baseres.BaseDatesList    
        ) returns baseres.BaseDatesList with null    
        {
    
            let tmpBaseDate := baseList->head with null    
            while tmpBaseDate != null {    
                let baseDate := baseList->GetBaseDatesList(tmpBaseDate) with null    
                tmpBaseDate := tmpBaseDate->next    
                baseDate->dateRangeList := CheckBaseClosures(baseDate->companyNo, baseType,     
                    baseDate->baseCode, baseDate->endBaseCode, reqRange)    
            }    
            return baseList    
        }
    
        if (holidayType = holtype.Club) {    
            clubBases := ProcessBases(requestRange, clubBases)    
            if clubBases = null or !clubBases->OpenBases() {    
                return false, "No club bases available"    
            }    
        } else if (holidayType = holtype.ClubYacht) {    
            clubBases := ProcessBases(requestRange, clubBases)    
            if clubBases = null {    
                return false, "No club bases available"    
            }    
            let tmp := (clubBases->head if clubBases != null, null otherwise) with null    
            while (tmp != null) {    
                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                yachtBases, yachtProduct := LinkedBases(baseres.YachtBase, yachtBases, baseDate,     
                                yachtStartBase, yachtEndBase)    
            }    
            if yachtBases = null {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            } else {    
                let openBases := clubBases->OpenBases() and yachtBases->OpenBases()    
                if !openBases {    
                    return false, "No club/yacht base combinations available"    
                }    
            }    
        } else if (holidayType = holtype.YachtClub) {    
            yachtBases := ProcessBases(requestRange, yachtBases)    
            if yachtBases = null {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            }    
            let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
            while (tmp != null) {    
                let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                clubBases, clubProduct := LinkedBases(baseres.ClubBase, clubBases, baseDate,     
                                clubStartBase, null)    
            }    
            if clubBases = null {    
                -- TO DO need to sort our error codes for web access    
                return false, "No club bases available"    
            } else {    
                let openBases := yachtBases->OpenBases() and clubBases->OpenBases()    
                if !openBases {    
                    return false, "No yacht/club base combinations available"    
                }    
            }    
        } else {    
            yachtBases := ProcessBases(requestRange, yachtBases)    
            yachtProduct := product    
            if yachtBases = null or !yachtBases->OpenBases() {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            }    
        }    
        return true, ""    
    }    
    
    --------------------------------------------------------------------------------------------------------------------------    
    private function BuildBases(    
        requestRange is baseres.DateRange    
    ) returns (boolean, string)    
    {    
        let isStartBase := true    
        let isEndBase := true    
        errMsg is string    
        baseTravelDur := travelDuration    
        if holidayType in (holtype.ClubYacht, holtype.YachtClub) {    
            isEndBase := false -- The second base will be the end base    
            baseTravelDur := baseTravelDur div 2    
        }    
        -- Determine the closed base's type depending on the requested holiday type.    
        baseType is baseres.BaseType    
        case holidayType {    
            value holtype.Club, holtype.ClubYacht    
                baseType := baseres.ClubBase    
            value holtype.Yacht, holtype.YachtClub    
                baseType := baseres.YachtBase    
            value holtype.Waterways    
                baseType := baseres.Waterways    
        }    
    
        --------------------------------------------------------------------------------------------------------------------------    
        function CheckBaseRestrictions(    
            startBase is string,    
            endBase is string with null    
        ) returns boolean    
        {
    
            --------------------------------------------------------------------------------------------------------------------------    
            function FindRestrictions(    
                startBase is string,    
                endBase is string    
            ) returns boolean    
            {
    
                -- Match restrictions for the combination of startBase base.F_base_code    
                -- add to restiction list if necessary    
                let isRestricted := false    
                select from baserest    
                where F_company_no = gl_company_no    
                and F_start_base = startBase    
                and F_end_base = endBase    
                {
    
                    let basePair := empty(avbk.BasePairElement)    
                    basePair->startBase := baserest.F_start_base    
                    basePair->endBase := baserest.F_end_base    
                    if restrictedBases = null {    
                        restrictedBases := empty(linkedlist.List)    
                    }    
                    if F_accom_no = 0 {    
                        call restrictedBases->Append(basePair)    
                        isRestricted := true    
                    } else {    
                        if restrictedBasesHash = null {    
                            restrictedBasesHash := empty(schash.Hash)    
                            call restrictedBasesHash->SetHashSize(211)    
                        }    
                        let ?, cls := restrictedBasesHash->Retrieve(string(F_accom_no)) with null    
                        if cls != null {    
                            let list := cast(cls, RestrictedAccomList)    
                            call list->Append(basePair)    
                        } else {    
                            let list := empty(RestrictedAccomList)    
                            call list->Append(basePair)    
                            ? := restrictedBasesHash->Enter(string(F_accom_no), list)    
                        }    
                    }    
                }
    
                    
                -- We also need to check if the turnaround numbers and berth space are ok    
                -- we need to create a dummy accmref tuple    
                let accrefTpl := empty(schema.accomref)    
                    
                accrefTpl->F_base_code := startBase    
                accrefTpl->F_end_base := endBase    
                --accrefTpl->F_accom_no := accomTu->F_accom_no    
                accrefTpl->F_start_date := requestRange->startDate    
                accrefTpl->F_end_date := requestRange->endDate     
                    
                if !book.check_turn_nos(accrefTpl)    
                {    
                    return true -- base is restricted    
                }
    
                return isRestricted    
            }
    
            --------------------------------------------------------------------------------------------------------------------------    
            allRestricted is boolean := true    
            if endBase in ("", null) {    
                    
                if showAvailableBases {    
                    select from base    
                    where F_area matches area    
                    and F_product != "OLD"    
                    and F_old_base = false    
                    {
    
                        -- Match restrictions for the combination of startBase base.F_base_code    
                        -- add to restiction list if necessary    
                        let isRestricted := FindRestrictions(startBase, base.F_base_code)    
                        allRestricted := (allRestricted and isRestricted)    
                        if showAvailableBases and base.F_base_code != startBase {    
                            -- Switch bases around to check for restictions    
                            isRestricted := FindRestrictions(base.F_base_code, startBase)    
                            allRestricted := (allRestricted and isRestricted)    
                        }    
    
                    }
    
                } else {    
                    allRestricted := false    
                }    
            } else {    
                -- Match restrictions for the combination of startBase endBase    
                let isRestricted := FindRestrictions(startBase, endBase)    
                allRestricted := (allRestricted and isRestricted)    
            }    
            return allRestricted     
        }
    
        --------------------------------------------------------------------------------------------------------------------------    
    
        function FindBase(    
            reqRange is baseres.DateRange,    
            startBase is string,    
            endBase is string with null,    
            baseList is baseres.BaseDatesList with null    
        ) returns (baseres.BaseDatesList with null, string with null)    
        {
    
                        let msg := ""    
                           
            -- TODO what about pub.NoRestrictions ??    
            let tu := empty(schema.base)    
            if baseList = null {    
                 baseList := empty(baseres.BaseDatesList)    
            }    
            if baseLinkList = null {    
                baseLinkList := empty(baseres.BaseLinkList)    
            }    
            if startBase matches "*[\*\|\?]*|$" {    
                select as tu from base    
                where F_base_code matches startBase    
                and F_area matches area    
                and F_product = product    
                and F_company_no = gl_company_no    
                and !F_old_base    
                and (F_max_dur = null or F_max_dur >= baseTravelDur)    
                {
    
                        
                    let actualEndBase := endBase    
                    if endBase in ("", null) and !showAvailableBases {    
                        actualEndBase := tu->F_base_code    
                    }    
                        
                    -- if tui then we want to add all linked bases from the baselink table    
                    if endBase = "ANY"    
                    {    
                        -- need to set showAnyYachtEndBase to true    
                        showAnyYachtEndBase := true    
                            
                        endBase := startBase    
                        actualEndBase := ""    
                    }    
                            
                            
                    let minDur := tu->F_min_dur    
                    if tu->F_base_code != actualEndBase and actualEndBase != null {    
                        let minOneWayDur := pub.GetMinOneWayDur(    
                            tu->F_base_code, actualEndBase) with null    
                        minDur := (minOneWayDur if minOneWayDur != null, minDur otherwise)    
                    }    
                        
                    if baseTravelDur < minDur {    
                            return null, stringid.Error("Duration is less than minimum duration allowed for this trip", gl_lang)    
                    }    
                    if CheckBaseRestrictions(tu->F_base_code, actualEndBase) {    
                        return null, stringid.Error("There is a restriction on this start/end base combination", gl_lang)    
                    }    
                        
                    -- Check for both start and end base closures.    
                    let dateRangeList := CheckBaseClosures(tu->F_company_no, baseType,     
                                tu->F_base_code, actualEndBase, reqRange) with null    
    
                    call baseList->Append(baseres.BuildBaseDates(tu->F_company_no,     
                        tu->F_base_code, actualEndBase, dateRangeList,     
                        isStartBase, isEndBase, F_deliv_reqd))    
                    call cache.EnterBase(tu)    
--<<JB TBD: Determine if we ever get yacht but no club results or club     
-- but no yacht resultswhen doing club/yacht or yacht/club searches.>>    
--                    if !(holidayType in (holtype.ClubYacht, holtype.YachtClub)) {    
                        ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                            tu->F_company_no, tu->F_base_code,     
                            pub.GetExtraBase(tu->F_base_code), null, null))    
--                    }    
                }
    
            } else {    
                -- product must be set    
                -- Add the premier bases to the result list as well.    
                select as tu from base    
                where F_product = product    
                and F_area matches area    
                and F_company_no = gl_company_no    
                and F_base_code = startBase    
                and !F_old_base    
                and (F_max_dur = null or F_max_dur >= baseTravelDur)    
                {
    
                    let actualEndBase := endBase    
                    if endBase in ("", null) and !showAvailableBases {    
                        actualEndBase := tu->F_base_code    
                    }    
                    let minDur := tu->F_min_dur    
                    if tu->F_base_code != actualEndBase and actualEndBase != null {    
                        let minOneWayDur := pub.GetMinOneWayDur(    
                            tu->F_base_code, actualEndBase) with null    
                        minDur := (minOneWayDur if minOneWayDur != null, minDur otherwise)    
                    }    
                    if baseTravelDur < minDur {    
                        reject    
                    }    
                    -- Check for both start and end base closures.    
                    let dateRangeList := CheckBaseClosures(tu->F_company_no, baseType,     
                                tu->F_base_code, actualEndBase, reqRange) with null    
    
                    call cache.EnterBase(tu)    
                    call baseList->Append(baseres.BuildBaseDates(tu->F_company_no,     
                        tu->F_base_code, actualEndBase, dateRangeList,     
                        isStartBase, isEndBase, F_deliv_reqd))    
--<<JB TBD: Determine if we ever get yacht but no club results or club     
-- but no yacht resultswhen doing club/yacht or yacht/club searches.>>    
--                    if !(holidayType in (holtype.ClubYacht, holtype.YachtClub)) {    
                        ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                            tu->F_company_no, tu->F_base_code,     
                            pub.GetExtraBase(tu->F_base_code), null, null))    
--                    }    
                    if (((isInternet and tu->F_pb_internet_use = 'I') or     
                        (!isInternet and tu->F_pb_internet_use = 'N') or     
                        (tu->F_pb_internet_use = 'B')) and tu->F_premier_base != "")    
                    {    
                        -- Check for premier base closures.    
                        let dateRangeList := CheckBaseClosures(tu->F_company_no, baseType,     
                            tu->F_premier_base, actualEndBase, reqRange) with null    
                        call baseList->Append(baseres.BuildBaseDates(    
                            tu->F_company_no, tu->F_premier_base, actualEndBase,     
                            dateRangeList, isStartBase, isEndBase, F_deliv_reqd))    
                    }    
                }
    
            }    
            return (null if baseList->IsEmpty(), baseList otherwise), msg    
        }
                
        
        --------------------------------------------------------------------------------------------------------------------------    
        --------------------------------------------------------------------------------------------------------------------------    
        --------------------------------------------------------------------------------------------------------------------------    
        if (holidayType = holtype.Club) {    
            clubBases, errMsg := FindBase(requestRange, clubStartBase, null, clubBases)    
            clubProduct := product    
            if clubBases = null or !clubBases->OpenBases() {    
                if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
        } else if (holidayType = holtype.ClubYacht) {    
            clubBases, errMsg := FindBase(requestRange, clubStartBase, null, clubBases)    
            if clubBases = null {    
                if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
            clubProduct := product    
            let tmp := (clubBases->head if clubBases != null, null otherwise) with null    
            while (tmp != null) {    
                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                yachtBases, yachtProduct := LinkedBases(baseres.YachtBase, yachtBases, baseDate,     
                                yachtStartBase, yachtEndBase)    
            }    
            if yachtBases = null {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            } else {    
                let openBases := clubBases->OpenBases() and yachtBases->OpenBases()    
                if !openBases {    
                    return false, "No club/yacht base combinations available"    
                }    
            }    
        } else if (holidayType = holtype.YachtClub) {    
            yachtBases, errMsg := FindBase(requestRange, yachtStartBase, yachtEndBase, yachtBases)    
            if yachtBases = null {    
                    if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
            yachtProduct := product    
            let tmp := (yachtBases->head if yachtBases != null, null otherwise)with null    
            while (tmp != null) {    
                let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                clubBases, clubProduct := LinkedBases(baseres.ClubBase, clubBases, baseDate,     
                                clubStartBase, null)    
            }    
            if clubBases = null {    
                -- TO DO need to sort our error codes for web access    
                return false, "No club bases available"    
            } else {    
                let openBases := yachtBases->OpenBases() and clubBases->OpenBases()    
                if !openBases {    
                    return false, "No yacht/club base combinations available"    
                }    
            }    
        } else {    
            yachtBases, errMsg := FindBase(requestRange, yachtStartBase, yachtEndBase, yachtBases)    
            yachtProduct := product    
            if yachtBases = null or !yachtBases->OpenBases() {    
                if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
        }    
        return true, ""    
    }    
    --------------------------------------------------------------------------------------------------------------------------    
    
    private function AVBKSearch(    
        accomNo is large number,    
        avbkDate is avbkdt.DateTime with null,    
        avbkDur is avbkdt.Duration,    
        fromBase is string,    
        toBase is string with null,    
        dateRange is avbkdt.DateTimeRange with null,    
        hasDelivery is boolean,    
        maxPax is small number,    
        singlesPax is small number with null,    
        hourly is boolean with null,        -- null -> false    
        ignoreAvail is boolean with null    --  ignore avail.f rows/or lack of    
    ) returns avbk.AccomResult with null    
    {    
 
        let rqt := empty(avbk.Request)    
        let baseList := restrictedBases with null    
        if restrictedBasesHash != null {    
            let ?, list := restrictedBasesHash->Retrieve(string(accomNo)) with null    
            if list != null {    
                let accomBaseList := cast(list, RestrictedAccomList) with null    
                if !accomBaseList->fullList {    
                    let tmp := (restrictedBases->head if (restrictedBases != null), null otherwise) with null    
                    while tmp != null {    
                        let basePair := cast(tmp, avbk.BasePairElement)    
                        let newBasePair := empty(avbk.BasePairElement)    
                        newBasePair->startBase := basePair->startBase    
                        newBasePair->endBase := basePair->endBase    
                        call accomBaseList->Append(newBasePair)    
                        tmp := tmp->next    
                    }    
                    accomBaseList->fullList := true    
                }    
                baseList := accomBaseList    
            }    
        }    
        call rqt->Init(    
            accomNo,    
            avbkDate,    
            avbkDur,    
            dateRange,    
            fromBase,    
            (null if showAnyYachtEndBase = true, toBase if (toBase != null or showAvailableBases), fromBase otherwise),    
            (showAvailableBases and yachtStartBase != "*" and showAnyYachtEndBase != true and !gl_istui),    
            baseList,    
            singlesPax,    
            hourly,    
            maxPax,    
            --(maxPax if singlesPax != null, null otherwise),    
            hasDelivery,    
            ignoreAvail)    
            
        let res := empty(avbk.Controller)->FindAccomResult(rqt)    
        --let d, t := avbkdt.DateAndTime(avbkDate)    
--display accomNo, res->accomDateList->elemCount, fromBase, toBase    
        return res    
    }    
    --------------------------------------------------------------------------------------------------------------------------    
            
    private function LinkedBases(    
        baseType is baseres.BaseType,    
        baseList is baseres.BaseDatesList with null,    
        baseDate is baseres.BaseDates,    
        startBase is string,    
        endBase is string with null    
    ) returns (baseres.BaseDatesList with null, string)    
    {    
        let linkedProduct := ""    
        quick select from baselink, base, prodpack    
        where baselink.F_company_no = baseDate->companyNo    
        and baselink.F_first_base = baseDate->baseCode    
        and baselink.F_second_base matches startBase    
        and baselink.F_link_type = baselnk.PrimaryLink    
        and base.F_company_no = baseDate->companyNo    
        and base.F_base_code = baselink.F_second_base    
        and !base.F_old_base    
        and prodpack.F_company_no = baseDate->companyNo    
        and prodpack.F_prod_code = base.F_product    
        and prodpack.F_pack_code matches package    
        order by F_priority    
        {
    
            let actualEndBase := endBase    
            if endBase in ("", null) {    
                actualEndBase := base.F_base_code    
            }    
            if linkedProduct = "" {    
                linkedProduct := base.F_product    
            }    
            if baseDate->dateRangeList != null {    
                let tmpDateRange := baseDate->dateRangeList->head with null    
                while tmpDateRange != null {    
                    let dateRange := baseDate->dateRangeList->GetDateRange(tmpDateRange) with null    
                    tmpDateRange := tmpDateRange->next    
                    let reqRange := empty(baseres.DateRange)    
                    reqRange->startDate := dateRange->startDate + baseTravelDur days    
                    reqRange->endDate := dateRange->endDate + baseTravelDur days    
    
                    -- Check for base closures.    
                    let dateRangeList := CheckBaseClosures(base.F_company_no, baseType,     
                        base.F_base_code, actualEndBase, reqRange) with null    
    
                    if dateRangeList = null or dateRangeList->IsEmpty() {    
                        ? := baseDate->dateRangeList->ElemDelete(dateRange)    
                    } else {    
                        let singleElem := (dateRangeList->elemCount = 1)    
                        let tmpFirstDate := dateRangeList->head with null    
                        if tmpFirstDate != null {    
                            let firstDates := dateRangeList->GetDateRange(    
                                        tmpFirstDate) with null    
                            if firstDates != null {    
                                dateRange->startDate := (firstDates->startDate -     
                                            baseTravelDur days)    
                                if singleElem {    
                                    dateRange->endDate := (firstDates->endDate -     
                                                baseTravelDur days)    
                                }    
                            }    
                        }    
                        if !singleElem {    
                            let tmpLastDates := dateRangeList->tail with null    
                            if tmpLastDates != null {     
                                let lastDates := dateRangeList->GetDateRange(    
                                            tmpLastDates) with null    
                                if lastDates != null {    
                                    dateRange->endDate := (lastDates->endDate -     
                                                baseTravelDur days)    
                                }    
                            }    
                        }    
                        if (baseList = null) {    
                            baseList := empty(baseres.BaseDatesList)    
                        }    
                        let unqBaseDate := baseList->UniqueAppend(baseres.BuildBaseDates(    
                            base.F_company_no, base.F_base_code, actualEndBase,     
                            dateRangeList, false, true, F_deliv_reqd)) with null    
                        unqBaseDate->dateRangeList := dateRangeList    
    
                        ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                            base.F_company_no, baseDate->baseCode,     
                            pub.GetExtraBase(baseDate->baseCode),     
                            actualEndBase, pub.GetExtraBase(actualEndBase)))    
                        -- TODO add schema.base to cache.    
                    }    
                }    
            } else {    
                if (baseList = null) {    
                    baseList := empty(baseres.BaseDatesList)    
                }    
                let unqBaseDate := baseList->UniqueAppend(baseres.BuildBaseDates(    
                    base.F_company_no, base.F_base_code, actualEndBase,     
                    null, false, true, F_deliv_reqd)) with null    
                unqBaseDate->dateRangeList := null    
    
                ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                    base.F_company_no, baseDate->baseCode,     
                    pub.GetExtraBase(baseDate->baseCode),     
                    actualEndBase, pub.GetExtraBase(actualEndBase)))    
                -- TODO add schema.base to cache.    
            }    
        }
    
        return (baseList if (baseList != null and !baseList->IsEmpty()), null otherwise), linkedProduct    
    }    
    
    ------------------------------------------------------------------------------------------------------    
    function ResultMatchYachtRequests(    
        yacht is accomres.YachtResult    
    ) returns boolean    
    {
    
        if accomRequests = null or    
           (accomRequests->yachtRequest = null and accomRequests->waterwaysRequest = null) {    
            return true    
        }
    
        if holidayType = holtype.Waterways {    
            let waterwaysRequest := accomRequests->waterwaysRequest    
            if waterwaysRequest->elite and !yacht->isPremier {    
                return false    
            }
    
        } else {    
            let yachtRequest := accomRequests->yachtRequest    
            if yachtRequest->premierYacht and !yacht->isPremier {    
                return false    
            }
    
        }    
        return true    
    }
    
    
    --------------------------------------------------------------------------------------------------------------------------    
    function MatchYachtRequests(    
        yacht is accomres.YachtResult with null,    
        accTypeTu is schema.acc_type    
    ) returns boolean    
    {
    
    
        -- Check numbers of pax for TuiG    
        if gl_istui {    
            let totPax := adultPax + childPax    
            if accTypeTu->F_min_sale > totPax or totPax > accTypeTu->F_max_sale {    
                return false    
            }
    
        } 
                
        -- premierYacht status must be checked later when we have the start date.    
        if accomRequests = null or    
           (accomRequests->yachtRequest = null and accomRequests->waterwaysRequest = null) {    
            return true    
        }
    
    
        if holidayType = holtype.Waterways {    
    
            let waterwaysRequest := accomRequests->waterwaysRequest    
            if waterwaysRequest->singleYachtAccom {    
                let totPax := adultPax + childPax    
                if waterwaysRequest->singles {    
                    if totPax > accTypeTu->F_max_singles {    
                        return false    
                    }
    
                } else {    
                    if accTypeTu->F_min_sale > totPax or totPax > accTypeTu->F_max_sale {    
                        return false    
                    }
    
                }    
            }    
            if yacht = null {    
                if waterwaysRequest->cabins > 0 and (accTypeTu->F_fw_cabins + accTypeTu->F_fs_cabins + accTypeTu->F_af_cabins < waterwaysRequest->cabins) {    
                    return false    
                }
    
                if waterwaysRequest->heads > 0 and accTypeTu->F_heads < waterwaysRequest->heads {    
                    return false    
                }
    
            } else {    
                if (waterwaysRequest->cabins > 0 and yacht->numCabins < waterwaysRequest->cabins) or    
                   (waterwaysRequest->heads > 0 and yacht->numHeads < waterwaysRequest->heads) {    
                    return false    
                }
    
                if waterwaysRequest->bowThrusters and !yacht->bowThrusters or    
                    waterwaysRequest->airCondition and !yacht->airCondition or    
                    waterwaysRequest->cdCassette and !yacht->cdCassette or    
                    waterwaysRequest->tableChairs and !yacht->tableChairs or    
                    (waterwaysRequest->buildYear > 0 and waterwaysRequest->buildYear > yacht->buildYear) or    
                    (waterwaysRequest->shorePower != "" and waterwaysRequest->shorePower != null     
                    and waterwaysRequest->shorePower != yacht->shorePower) or    
                    (waterwaysRequest->noOfSteerPos != "" and waterwaysRequest->noOfSteerPos != null and    
                    waterwaysRequest->noOfSteerPos != yacht->noOfSteerPos) {    
                    return false    
                }
    
                if waterwaysRequest->singles and !yacht->okSingles {    
                    return false    
                }
    
            }    
        } else {    
            let yachtRequest := accomRequests->yachtRequest    
            if yacht = null {    
                if yachtRequest->cabins > 0 and (accTypeTu->F_fw_cabins + accTypeTu->F_fs_cabins + accTypeTu->F_af_cabins != yachtRequest->cabins) {    
                    return false    
                }
    
                if yachtRequest->heads > 0 and accTypeTu->F_heads != yachtRequest->heads {    
                    return false    
                }
    
            } else {    
                let totPax := adultPax + childPax    
                if yachtRequest->singleYachtAccom {    
                    if yachtRequest->singles {    
                        if totPax > yacht->maxSingles {    
                            return false    
                        }
    
                    } else {    
                        if yacht->minPax > totPax or totPax > yacht->maxPax {    
                            return false    
                        }
    
                    }    
                }    
                if (yachtRequest->cabins > 0 and yacht->numCabins != yachtRequest->cabins) or    
                   (yachtRequest->heads > 0 and yacht->numHeads != yachtRequest->heads) {    
                    return false    
                }
    
                if yachtRequest->anchorWinch and !yacht->windlass {    
                    return false    
                }
    
                if yachtRequest->autopilot and !yacht->autoPilot {    
                    return false    
                }
    
                if yachtRequest->mainSail != "" and yachtRequest->mainSail != null and     
                   yachtRequest->mainSail != yacht->mainSail {    
                    return false    
                }
    
                if yachtRequest->singles and !yacht->okSingles {    
                    return false    
                }
    
            }    
        }    
        return true    
    }
    
    --------------------------------------------------------------------------------------------------------------------------    
    
    procedure YachtAvailability(    
        yachtSpec is accomres.YachtResult with null,    
        baseCode is string,    
        baseDate is baseres.BaseDates,    
        dateResult is dateres.DateResult with null,    
        yacht is accomres.YachtResult    
    )    
    {
    
 
        let singlesReqd := SinglesReqd(true)    
        let maxPax := (yacht->maxSingles if singlesReqd, yacht->maxPax otherwise)    
        let paxReqd := ((adultPax + childPax) if (SingleAccomReqd(true) & singlesReqd),     
                1 if singlesReqd, null otherwise)    
            if dateResult = null {    
            let dateRangeList := baseDate->dateRangeList    
            let tmpDate := dateRangeList->head with null    
            while (tmpDate != null) {    
                let dateRange := dateRangeList->GetDateRange(tmpDate)    
                avbkDate is avbkdt.DateTime with null    
                avbkDateRange is avbkdt.DateTimeRange with null    
                if leaway = 0 {    
                    avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                } else {    
                    avbkDateRange := empty(avbkdt.DateTimeRange)->Init(    
                            dateRange->startDate, dateRange->endDate)    
                }    
--                let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)    
                let avbkDur := avbkdt.DaysToDuration(baseTravelDur)    
                    
                let res := AVBKSearch(yacht->accomNo, avbkDate, avbkDur, baseDate->baseCode,     
                        baseDate->endBaseCode, avbkDateRange, baseDate->hasDelivery,     
                        maxPax, paxReqd) with null    
                        -- hourly    
                        -- ignoreAvail     
                call BuildResults(baseDate, null, yacht, res, baseres.YachtBase, avbkDate, avbkDur, singlesReqd, null, yachtSpec)    
                tmpDate := tmpDate->next    
            }    
        } else {    
            let startDate := dateResult->startDate    
            if holidayType = holtype.ClubYacht {    
                startDate := startDate + 7 days    
            }    
            let avbkDate := avbkdt.DateToMidday(startDate)    
            let avbkDur := dateResult->travelDuration    
            let res := AVBKSearch(yacht->accomNo, avbkDate, avbkDur, baseDate->baseCode,     
                    baseDate->endBaseCode, null, baseDate->hasDelivery,     
                    maxPax, paxReqd) with null    
                    -- hourly    
                    -- ignoreAvail     
            call BuildResults(baseDate, null, yacht, res, baseres.YachtBase, avbkDate, avbkDur, singlesReqd)    
        }    
    }
    
    
    --------------------------------------------------------------------------------------------------------------------------    
    public procedure BuildYachtList(    
        yachtSpec is accomres.YachtResult with null    
    )    
    {
    
        let accTypeTu := empty(schema.acc_type)    
        let accomTu := empty(schema.accom)    
        let catTypeTu := empty(schema.cat_type)    
    
        if yachtBases = null or yachtBases->IsEmpty() {    
            return    
        }    
            
        -----------------------------------------------------------------------------    
        procedure ProcessYacht(    
            baseCode is string,    
            baseDate is baseres.BaseDates,    
            dateResult is dateres.DateResult with null    
        )    
        {
    
  
            let yacht := accomres.BuildYachtResultFromAccom(accomTu, accTypeTu, holidayType)    
            yacht->category := catTypeTu->F_category    
            yacht->sortBy := catTypeTu->F_sort_by    
            yacht->accomType := accomTu->F_type    
            if !MatchYachtRequests(yacht, accTypeTu) {    
                return    
            }    
                
            if yachtSpec != null and dateResult != null {    
                call yacht->SetPremier(dateResult->startDate)    
                if !yacht->IsSameYacht(yachtSpec) {    
                    -- If specification of yacht is not the same as required, then ignore it.    
                    return    
                }    
            }    
            call baseDate->yachtList->Append(yacht)    
            if showHeldBookings {    
                if baseDate->categoryList = null {    
                    baseDate->categoryList := empty(accomres.CategoryList)    
                }    
                let cce := empty(accomres.YachtCategoryElement)    
                cce->category := yacht->category    
                cce->sortBy := yacht->sortBy    
                cce->accomType := yacht->accomType    
                if dateResult != null    
                {    
                    call cce->setPriceList(baseCode,baseDate->endBaseCode,yacht->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc, adultPax, childPax)    
                }    
                ? := baseDate->categoryList->YachtUniqueAppend(cce)    
            }    
                
            call YachtAvailability(yachtSpec, baseCode, baseDate, dateResult, yacht)    
        }
    
    
        -----------------------------------------------------------------------------    
    
        procedure SearchAllTypes()    
        {
    
            hashinst is schash.Hash with null    
            procedure AccomSearch(    
                baseDate is baseres.BaseDates,    
                dateResult is dateres.DateResult with null,    
                dateResList is dateres.DateResultList with null    
            )    
            {
    
                -----------------------------------------------------------------------------    
                procedure Process(    
                    baseDate is baseres.BaseDates,    
                    dateResult is dateres.DateResult with null,    
                    dateResList is dateres.DateResultList with null    
                )    
                {
    
                    quick select as accTypeTu from acc_type    
                    where acc_type.F_type = catTypeTu->F_type    
                    order by F_loa_feet, F_avail_desc    
                    on ex.lock {
    
                        --call myerror("One or more acc_type records skipped",2)    
                        accept    
                    }
    
                    {    
                        
                        let keyStr := gl_company_no^accomTu->F_accom_no^baseDate->baseCode^(string(dateResult->startDate) if dateResult != null, "" otherwise)    
                            
                        let uniqueEntry, ? := hashinst->UniqueEnter(keyStr)    
                        if uniqueEntry {    
                            if dateResList != null {    
                                let dateTmp := dateResList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart and dateRes->isValid {    
                                        call ProcessYacht(baseDate->baseCode, baseDate, dateRes)    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            } else {    
                                call ProcessYacht(baseDate->baseCode, baseDate, dateResult)    
                            }    
                        }    
                    }    
                }
    
                -----------------------------------------------------------------------------    
    
                if baseDate->yachtList = null {    
                    baseDate->yachtList := empty(accomres.YachtList)    
                }    
                gl_company_no := baseDate->companyNo    
                quick select unique avail.F_company_no, avail.F_base,    
                avail.F_accom_no, avail.F_display, avail.F_access    
                from avail index F_key_2    
                where avail.F_company_no = gl_company_no    
                and avail.F_base = baseDate->baseCode    
                and avail.F_display != "N"    
                and pub.AvailAccessOk(avail.F_access)    
                on ex.lock {
    
                    --call myerror("One or more avail records skipped",2)    
                    accept    
                }
    
                {    
                    quick select as accomTu from accom index F_accom_no    
                    where accom.F_accom_no = avail.F_accom_no    
                    and accom.F_type matches yachtType    
                    and fleet.CheckFleet(F_fleet)    
                    on ex.lock {
    
                        --call myerror("One or more accom records skipped",0)    
                        accept    
                    }
    
                    {    
                        if yachtCat = 0 {    
                            quick select as catTypeTu from cat_type index F_key    
                            where cat_type.F_product = yachtProduct    
                            and cat_type.F_company_no = gl_company_no    
                            and cat_type.F_type = accom.F_type    
                            order by F_category,F_sort_by    
                            on ex.lock {
    
                                --call myerror("One or more cat_type records skipped",2)    
                                accept    
                            }
    
                            {    
                                call Process(baseDate, dateResult, dateResList)    
                            }    
                        } else {    
                            quick select as catTypeTu from cat_type index F_key    
                            where cat_type.F_product = yachtProduct    
                            and cat_type.F_company_no = gl_company_no    
                            and cat_type.F_type = accom.F_type    
                            and cat_type.F_category = yachtCat    
                            order by F_category,F_sort_by    
                            on ex.lock {
    
                                --call myerror("One or more cat_type records skipped",2)    
                                accept    
                            }
    
                            {    
                                call Process(baseDate, dateResult, dateResList)    
                            }    
                        }    
                    }    
                }    
            }
    
    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -- body of SearchAllTypes    
    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
            if dateResultList = null or dateResultList->IsEmpty() {    
                let tmp := yachtBases->head with null    
                while (tmp != null) {    
                    let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                    call AccomSearch(baseDate, null)    
                    tmp := tmp->next    
                }    
                    
                    
            } else {    
                if holidayType = holtype.ClubYacht {    
                    -- TODO filter out end bases where start base is unavailable    
                    let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
                    while (tmp != null) {    
                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                        call AccomSearch(baseDate, null, dateResultList)    
                        tmp := tmp->next    
                    }    
                } else {    
                    let dateTmp := dateResultList->head with null    
                    while (dateTmp != null) {    
                        let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                        if dateRes->isStart and dateRes->isValid {    
                            let baseResultList := dateRes->baseResultList    
                            let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                            while baseTmp != null {    
                                let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                if baseResult->isValid {    
                                    let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
                                    while (tmp != null) {    
                                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                        if baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                            call AccomSearch(baseDate, dateRes)    
                                        }    
                                        tmp := tmp->next    
                                    }    
                                }    
                                baseTmp := baseTmp->next    
                            }    
                        }    
                        dateTmp := dateTmp->next    
                    }    
                        
                }    
            }    
        }
     
    
        -----------------------------------------------------------------------------    
        procedure SearchThisType()    
        {
    
    
            hashinst is schash.Hash with null    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
    
            -----------------------------------------------------------------------------    
            procedure Process()    
            {
    
                -----------------------------------------------------------------------------    
                procedure AvailSearch(    
                    baseDate is baseres.BaseDates,    
                    dateResult is dateres.DateResult with null,    
                    dateResList is dateres.DateResultList with null    
                )    
                {
    
                    if baseDate->yachtList = null {    
                        baseDate->yachtList := empty(accomres.YachtList)    
                    }    
                    quick select unique avail.F_company_no, avail.F_base,    
                    avail.F_accom_no, avail.F_display,avail.F_access    
                    from avail index F_key    
                    where avail.F_company_no = gl_company_no    
                    and avail.F_base = baseDate->baseCode    
                    and avail.F_accom_no = accomTu->F_accom_no    
                    and avail.F_display != "N"    
                    and pub.AvailAccessOk(avail.F_access)    
                    on ex.lock {
    
                        --call myerror("One or more avail records skipped",2)    
                        accept    
                    }
    
                    {    
                        let keyStr := gl_company_no^accomTu->F_accom_no^baseDate->baseCode^(string(dateResult->startDate) if dateResult != null, "" otherwise)    
                        let uniqueEntry, ? := hashinst->UniqueEnter(keyStr)    
                        if uniqueEntry {    
                            if dateResList != null {    
                                let dateTmp := dateResList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart {    
                                        call AvailSearch(baseDate, dateRes)    
                                        call ProcessYacht(baseDate->baseCode, baseDate, dateRes)    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            } else {    
                                call ProcessYacht(baseDate->baseCode, baseDate, dateResult)    
                            }    
                        }    
                    }    
                }
    
                -----------------------------------------------------------------------------    
                quick select as accTypeTu from acc_type    
                where acc_type.F_type = catTypeTu->F_type    
                order by F_loa_feet, F_avail_desc    
                on ex.lock {
    
                    --call myerror("One or more acc_type records skipped",2)    
                    accept    
                }
    
                {    
                    if MatchYachtRequests(null, accTypeTu) {    
                        quick select as accomTu from accom    
                        where accom.F_type = acc_type.F_type    
                        and fleet.CheckFleet(F_fleet)    
                        order by F_category,F_name    
                        on ex.lock {
    
                            --call myerror("One or more accom records skipped",2)    
                            accept    
                        }
    
                        {    
                            if dateResultList = null  or dateResultList->IsEmpty() {    
                                let tmpBase := yachtBases->head with null    
                                while (tmpBase != null) {    
                                    let baseDate := yachtBases->GetBaseDatesList(tmpBase) with null    
                                    if gl_company_no = baseDate->companyNo {    
                                        call AvailSearch(baseDate, null, null)    
                                    }    
                                    tmpBase := tmpBase->next    
                                }    
                            } else {    
                                if holidayType = holtype.ClubYacht {    
                                    -- TODO filter out end bases where start base is unavailable    
                                    let tmp := yachtBases->head with null    
                                    while (tmp != null) {    
                                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                        call AvailSearch(baseDate, null, dateResultList)    
                                        tmp := tmp->next    
                                    }    
                                } else {    
                                    let dateTmp := dateResultList->head with null    
                                    while (dateTmp != null) {    
                                        let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                        let baseResultList := dateRes->baseResultList    
                                        let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                                        if dateRes->isStart and dateRes->isValid {    
                                            while baseTmp != null {    
                                                let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                                if baseResult->isValid {    
                                                    let tmp := yachtBases->head with null    
                                                    while (tmp != null) {    
                                                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                                        if gl_company_no = baseDate->companyNo and    
        --    ###### TO DO doesn't work for second part of hol ##    
                                                           baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                                            call AvailSearch(baseDate, dateRes)    
                                                        }    
                                                        tmp := tmp->next    
                                                    }    
                                                }    
                                                baseTmp := baseTmp->next    
                                            }    
                                        }    
                                        dateTmp := dateTmp->next    
                                    }    
                                }    
                            }    
                        }    
                    }    
                }    
            }
    
    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -- body of SearchThisType    
    
            let compArr := Companies(yachtBases)    
            let compCnt := 1    
            while compArr[compCnt] != "" {    
                gl_company_no := compArr[compCnt]    
                if yachtCat = 0 {    
                    quick select as catTypeTu from cat_type index F_key    
                    where cat_type.F_product = yachtProduct    
                    and cat_type.F_company_no = gl_company_no    
                    and cat_type.F_type matches yachtType    
                    order by F_category,F_sort_by    
                    on ex.lock {
    
                        --call myerror("One or more cat_type records skipped",2)    
                        accept    
                    }
    
                    {    
                        call Process()    
                    }    
                } else {    
                    quick select as catTypeTu from cat_type index F_key    
                    where cat_type.F_product = yachtProduct    
                    and cat_type.F_company_no = gl_company_no    
                    and cat_type.F_type matches yachtType    
                    and cat_type.F_category = yachtCat    
                    order by F_category,F_sort_by    
                    on ex.lock {
    
                        --call myerror("One or more cat_type records skipped",2)    
                        accept    
                    }
    
                    {    
                        call Process()    
                    }    
                }    
                compCnt := compCnt + 1    
            }    
        }
    
    
        -----------------------------------------------------------------------------    
        --njh  
        procedure SearchThisAccom()    
        {
    
    
            hashinst is schash.Hash with null    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
    
            procedure ProcessSingleYacht()    
            {
    
                procedure AvailSearch(    
                    baseDate is baseres.BaseDates,    
                    dateResult is dateres.DateResult with null,    
                    dateResList is dateres.DateResultList with null    
                )    
                {
    
                    if baseDate->yachtList = null {    
                        baseDate->yachtList := empty(accomres.YachtList)    
                    }    
                    quick select unique avail.F_company_no, avail.F_base,    
                    avail.F_accom_no, avail.F_display,avail.F_access    
                    from avail index F_key    
                    where avail.F_company_no = gl_company_no    
                    and avail.F_base = baseDate->baseCode    
                    and avail.F_accom_no = accomTu->F_accom_no    
                    and avail.F_display != "N"    
                    and pub.AvailAccessOk(avail.F_access)    
                    on ex.lock {
    
                        --call myerror("One or more avail records skipped",2)    
                        accept    
                    }
    
                    {    
                        let keyStr := gl_company_no^accomTu->F_accom_no^baseDate->baseCode^(string(dateResult->startDate) if dateResult != null, "" otherwise)    
                        let uniqueEntry, ? := hashinst->UniqueEnter(keyStr)    
                        if uniqueEntry {    
                            if dateResList != null {    
                                let dateTmp := dateResList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart {    
                                        call AvailSearch(baseDate, dateRes)    
                                        call ProcessYacht(baseDate->baseCode, baseDate, dateRes)    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            } else {    
                                call ProcessYacht(baseDate->baseCode, baseDate, dateResult)    
                            }    
                        }    
                    }    
                }
    
                -------------------------------------------------------------------------------------  
                -- body of ProcessSingleYacht  
  
                quick select as accTypeTu from acc_type    
                where acc_type.F_type = accomTu->F_type    
                on ex.lock {
  accept  }
    
                {   
  
                    quick select as catTypeTu from cat_type index F_key    
                    where cat_type.F_product = yachtProduct    
                    and cat_type.F_company_no = gl_company_no    
                    and cat_type.F_type = accomTu->F_type         
                    on ex.lock {
  accept  }
    
                    {}    
  
                    if (MatchYachtRequests(null, accTypeTu) and fleet.CheckFleet(accomTu->F_fleet))    
                    {    
                        if dateResultList = null  or dateResultList->IsEmpty() {    
                            let tmpBase := yachtBases->head with null    
                            while (tmpBase != null) {    
                                let baseDate := yachtBases->GetBaseDatesList(tmpBase) with null    
                                if gl_company_no = baseDate->companyNo {    
                                    call AvailSearch(baseDate, null, null)    
                                }    
                                tmpBase := tmpBase->next    
                            }    
                        } else {    
                            if holidayType = holtype.ClubYacht {    
                                -- TODO filter out end bases where start base is unavailable    
                                let tmp := yachtBases->head with null    
                                while (tmp != null) {    
                                    let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                    call AvailSearch(baseDate, null, dateResultList)    
                                    tmp := tmp->next    
                                }    
                            } else {    
                                let dateTmp := dateResultList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                    let baseResultList := dateRes->baseResultList    
                                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                                    if dateRes->isStart and dateRes->isValid {    
                                        while baseTmp != null {    
                                            let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                            if baseResult->isValid {    
                                                let tmp := yachtBases->head with null    
                                                while (tmp != null) {    
                                                    let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                                    if gl_company_no = baseDate->companyNo and    
    --    ###### TO DO doesn't work for second part of hol ##    
                                                    baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                                        call AvailSearch(baseDate, dateRes)    
                                                    }    
                                                    tmp := tmp->next    
                                                }    
                                            }    
                                            baseTmp := baseTmp->next    
                                        }    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            }    
                        }    
                    }    
                }    
            }
    
            ---------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -- body of SearchThisAccom    
    
            let compArr := Companies(yachtBases)    
            let compCnt := 1    
            while compArr[compCnt] != "" {    
                gl_company_no := compArr[compCnt]    
                select as accomTu from accom    
                where F_accom_no = yachtAccomNo
                {
    
                    call ProcessSingleYacht()    
                }
     
                compCnt := compCnt + 1    
            }    
        }
    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
        -- body of BuildYachtList    
    
        if (yachtAccomNo = 0)    
        { 
            if (yachtType = "*")    
            {    
                call    SearchAllTypes()    
            }    
            else    
            {    
                call    SearchThisType()    
            } 
        } 
        else    
        {    
            call    SearchThisAccom()    
        }    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
    }
    
        ---------------------------------------------------------------------------------------------------------------------------------------------------------    
    function ResultMatchClubRequests(    
        room is accomres.RoomResult    
    ) returns boolean    
    {
    
        if accomRequests = null or accomRequests->clubRequest = null {    
            return true    
        }
    
        let clubRequest := accomRequests->clubRequest    
        if clubRequest->adultOnly and !room->adultsOnly {    
            return false    
        }
    
        return true    
    }
    
    ------------------------------------------------------------------------------------------------------    
    function InvalidAccomForPax(    
        clientNo is large number,    
        accomPaxCat is string,    
        totalBedSpace is number,    
        adultKidPax is number    
    ) returns boolean    
    {
    
        invalidAccomForPax is boolean := false    
        cotPax is number := 1    
        let endDate := startDate + travelDuration days    
        select pass.F_client_no, pass.F_pass_no    
        from pass index F_key    
        where pass.F_client_no = clientNo    
        {
    
            let passngrAge, ? := passlink.GetPassengerAge(clientNo, pass.F_pass_no, endDate)    
            let paxType := passlink.GetAccomAgeCat(passngrAge)    
                
            case true {    
                value (paxType = passlink.GYBPax & accomPaxCat = "A")    
                    invalidAccomForPax := true    
                value (paxType = passlink.SUPax & accomPaxCat in ("A", "F"))    
                    invalidAccomForPax := true    
                value (paxType = passlink.SNAPPax & accomPaxCat in ("A", "F", "E"))    
                    invalidAccomForPax := true    
                value (paxType in (passlink.MINPax, passlink.COTPax))     
                    if (accomPaxCat in ("A", "F", "E", "D") or ((adultKidPax + cotPax) > totalBedSpace))    
                    {    
                        invalidAccomForPax := true    
                    } else {    
                        cotPax := cotPax + 1    
                    }    
            }    
        }
    
        return invalidAccomForPax    
    }
    
    ------------------------------------------------------------------------------------------------------    
    function MatchClubRequests(    
        accomTu is schema.accom    
    ) returns boolean    
    {
    
        -- Adults only checks can only be made when we have the date.    
        if accomRequests = null or accomRequests->clubRequest = null {    
            return true    
        }
    
        let clubRequest := accomRequests->clubRequest    
        if clubRequest->singleClubAccom {    
            let totPax := adultPax + childPax    
            let maxPax := accomTu->F_max_sale    
            let totBeds := ((accomTu->F_dbl_beds * 2) + accomTu->F_sng_beds + accomTu->F_tot_xtra_beds)    
            if clubRequest->singles {    
                maxPax := accomTu->F_max_singles    
                if totPax > accomTu->F_max_singles {    
                    return false    
                }
    
            } else {     
                if accomTu->F_min_sale > totPax or totPax > accomTu->F_max_sale {    
                    return false    
                }
    
            }    
            if (partyClientNo != null) {    
                if InvalidAccomForPax(partyClientNo, accomTu->F_ok_child, totBeds, totPax) {    
                    return false    
                }
    
            } else {    
                if (accomTu->F_ok_child in ("A", "F") & childPax >= 1) {    
                    return false    
                }
    
            }    
        }    
        if clubRequest->balcony and accomTu->F_balcony != 'Y' {    
            return false    
        }
    
        if clubRequest->seaView and accomTu->F_sea_view != 'Y' {    
            return false    
        }
    
        if clubRequest->singles and accomTu->F_max_singles < 1 {    
            return false    
        }
    
        if clubRequest->cots and accomTu->F_cots = 0 {    
            return false    
        }
    
        if clubRequest->zbeds and accomTu->F_dbl_zbeds = 0 and    
           accomTu->F_sng_zbeds = 0 {    
            return false    
        }
    
        return true    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    procedure RoomAvailability(    
        roomSpec is accomres.RoomResult with null,    
        baseCode is string,    
        baseDate is baseres.BaseDates,    
        dateResult is dateres.DateResult with null,    
        room is accomres.RoomResult    
    )    
     {
    
         let singlesReqd := SinglesReqd(false)    
        let maxPax := (room->maxSingles if singlesReqd, room->maxPax otherwise)    
        let paxReqd := ((adultPax + childPax) if (SingleAccomReqd(false) & singlesReqd),     
                1 if singlesReqd, null otherwise)    
        if dateResult == null {    
            let dateRangeList := baseDate->dateRangeList    
            let tmpDate := dateRangeList->head with null    
            while (tmpDate != null) {    
                let dateRange := dateRangeList->GetDateRange(tmpDate)    
--                let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                let avbkDur := avbkdt.DaysToDuration(baseTravelDur)    
                avbkDate is avbkdt.DateTime with null    
                avbkDateRange is avbkdt.DateTimeRange with null    
                if leaway = 0 {    
                    avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                } else {    
                    avbkDateRange := empty(avbkdt.DateTimeRange)->Init(    
                                dateRange->startDate, dateRange->endDate)    
                }    
                let res := AVBKSearch(room->accomNo, avbkDate, avbkDur, baseDate->baseCode,     
                        baseDate->baseCode, avbkDateRange, baseDate->hasDelivery,     
                        maxPax, paxReqd) with null    
                        -- hourly    
                        -- ignoreAvail     
                call BuildResults(baseDate, room, null, res, baseres.ClubBase, avbkDate, avbkDur, singlesReqd, roomSpec, null)    
                tmpDate := tmpDate->next    
            }    
        } else {    
            let startDate := dateResult->startDate    
            if holidayType = holtype.YachtClub {    
                startDate := startDate + 7 days    
            }    
            let avbkDate := avbkdt.DateToMidday(startDate)    
            let avbkDur := dateResult->travelDuration    
            let res := AVBKSearch(room->accomNo, avbkDate, avbkDur, baseCode, baseCode, null,    
                    false, maxPax, paxReqd) with null    
                    -- hourly    
                    -- ignoreAvail     
            call BuildResults(baseDate, room, null, res, baseres.ClubBase, avbkDate, avbkDur, singlesReqd)    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    -- if roomSpec then only select rooms that match the criteria    
    public procedure BuildClubList(    
        roomSpec is accomres.RoomResult with null    
    )    
    {
    
        let catAccTu := empty(schema.cat_acc)    
        let accomTu := empty(schema.accom)    
    
        if clubBases = null or clubBases->IsEmpty() {    
            return    
        }    
    
        procedure ProcessRoom(    
            baseCode is string,    
            baseDate is baseres.BaseDates,    
            dateResult is dateres.DateResult with null    
        )    
        {
    
            let room := accomres.BuildRoomResultFromAccom(accomTu, baseCode, adultPax, childPax, infantPax)    
            room->category := catAccTu->F_category    
            room->sortBy := catAccTu->F_sort_by    
            room->accomType := accomTu->F_type    
            if doInterconnecting in (InterconnectingOnly, NoInterconnecting, StdPlusInterconnecting) {    
                select * from accomrel    
                where F_accom_no = room->accomNo    
                and F_rel_level = "I"    
                {
    
                    let tu := empty(schema.accom)    
                    quick select as tu from accom index F_accom_no    
                    where accom.F_accom_no = accomrel.F_rel_accom_no    
                    {
    
                        
                        let relRoom := accomres.BuildRoomResultFromAccom(tu, baseCode, adultPax, childPax, infantPax)    
                        relRoom->relatedRoomType := F_rel_level    
                        if room->relatedRoomList = null {    
                            room->relatedRoomList := empty(accomres.RoomList)    
                        }    
                        call room->relatedRoomList->Append(relRoom)    
                    }
    
                }
    
            }    
            if roomSpec != null and dateResult != null {    
                call room->SetAdultsOnly(dateResult->startDate, (dateResult->startDate + avbkdt.DurationToDays(dateResult->travelDuration) days))    
                if dateResult != null and !room->IsSameRoom(roomSpec) {    
                    -- If specification of room is not the same as required, then ignore it.    
                    return    
                }    
            }    
            if (doInterconnecting = AllRooms or    
               (doInterconnecting = InterconnectingOnly and (room->relatedRoomList != null and !room->relatedRoomList->IsEmpty())) or    
               (doInterconnecting = NoInterconnecting and (room->relatedRoomList = null or room->relatedRoomList->IsEmpty())) or    
               doInterconnecting = StdPlusInterconnecting) {    
                call baseDate->roomList->Append(room)    
                if showHeldBookings {    
                    if baseDate->categoryList = null {    
                        baseDate->categoryList := empty(accomres.CategoryList)    
                    }    
                    let cce := empty(accomres.ClubCategoryElement)    
                    cce->category := room->category    
                    cce->sortBy := room->sortBy    
                    cce->accomType := room->accomType    
                    ? := baseDate->categoryList->ClubUniqueAppend(cce)    
                    if isInternet {    
                        call cce->setInetCat(baseCode,room->accomType,gl_company_no)    
                        call cce->setPriceList(baseCode,baseDate->endBaseCode,room->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc, adultPax, childPax)    
                    }    
                }    
                call RoomAvailability(roomSpec, baseCode, baseDate, dateResult, room)    
            }    
        }
    
        
        procedure    
        SearchByAvail(    
            baseCode is string,    
            baseDate is baseres.BaseDates with null,    
            dateResult is dateres.DateResult with null    
        )    
        {
    
            hashinst is schash.Hash with null    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
            quick select unique avail.F_company_no, avail.F_base,    
                avail.F_accom_no, avail.F_display,avail.F_access    
            from avail index F_key_2    
            where avail.F_company_no = gl_company_no    
            and avail.F_base = baseCode    
            and avail.F_display != "N"    
            and pub.AvailAccessOk(avail.F_access)    
            on ex.lock {
    
                --call myerror("One or more avail records skipped",2)    
                accept    
            }
    
            {    
                quick select as accomTu from accom index F_accom_no    
                where accom.F_accom_no = avail.F_accom_no    
                and accom.F_type matches clubType    
                on ex.lock {
    
                    --call myerror("One or more accom records skipped",0)    
                    accept    
                }
    
                {    
                    if MatchClubRequests(accomTu) {    
                        if clubCat = 0 {    
                            quick select as catAccTu from cat_acc    
                            where cat_acc.F_product = clubProduct    
                            and cat_acc.F_company_no = gl_company_no    
                            and cat_acc.F_accom_no = accomTu->F_accom_no    
                            order by cat_acc.F_category,cat_acc.F_sort_by    
                            on ex.lock {
    
                                --call myerror("One or more cat_acc records skipped",0)    
                                accept    
                            }
    
                            {    
                                let uniqueEntry, ? := hashinst->UniqueEnter(string(gl_company_no^accom.F_accom_no), null)    
                                if uniqueEntry {    
                                    call ProcessRoom(baseCode, baseDate, dateResult)    
                                }    
                            }    
                        } else {    
                            quick select as catAccTu from cat_acc    
                            where cat_acc.F_product = clubProduct    
                            and cat_acc.F_company_no = gl_company_no    
                            and cat_acc.F_accom_no = accomTu->F_accom_no    
                            and cat_acc.F_category = clubCat    
                            order by cat_acc.F_category,cat_acc.F_sort_by    
                            on ex.lock {
    
                                --call myerror("One or more cat_acc records skipped",0)    
                                accept    
                            }
    
                            {    
                                let uniqueEntry, ? := hashinst->UniqueEnter(string(gl_company_no^accom.F_accom_no), null)    
                                if uniqueEntry {    
                                    call ProcessRoom(baseCode, baseDate, dateResult)    
                                }    
                            }    
                        }    
                    }    
                }    
            }    
        }
    
    
        procedure    
        SearchByCat(    
        )    
        {
    
            procedure AvailSearch(    
                accomNo is large number,    
                baseDate is baseres.BaseDates with null,    
                dateResult is dateres.DateResult with null    
            )    
            {
    
                quick select from avail index F_key    
                where avail.F_company_no = baseDate->companyNo    
                and avail.F_accom_no = accomNo    
                and avail.F_base = baseDate->baseCode    
                and avail.F_display != "N"    
                and pub.AvailAccessOk(avail.F_access)    
                on ex.lock {
    
                    --call myerror("One or more avail records skipped",2)    
                    accept    
                }
    
                {    
                    call ProcessRoom(baseDate->baseCode, baseDate, dateResult)    
                    stop    
                }    
            }
    
    
            procedure AccomSearch()    
            {
    
                quick select as accomTu from accom index F_accom_no    
                where accom.F_accom_no = catAccTu->F_accom_no    
                and accom.F_type matches clubType    
                on ex.lock {
    
                    --call myerror("One or more accom records skipped",0)    
                    accept    
                }
    
                {    
                    if MatchClubRequests(accomTu) {    
                        if dateResultList == null {    
                            let tmp := clubBases->head with null    
                            while (tmp != null) {    
                                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                if gl_company_no = baseDate->companyNo {    
                                    if baseDate->roomList = null {    
                                        baseDate->roomList := empty(accomres.RoomList)    
                                    }    
                                    call AvailSearch(accom.F_accom_no, baseDate, null)    
                                }    
                                tmp := tmp->next    
                            }    
                        } else {                                
                            if holidayType = holtype.YachtClub {    
                                -- TODO filter out end bases where start base is unavailable    
                                let tmp := clubBases->head with null    
                                while (tmp != null) {    
                                    let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                    if gl_company_no = baseDate->companyNo {    
                                        if baseDate->roomList = null {    
                                            baseDate->roomList := empty(accomres.RoomList)    
                                        }    
                                        let dateTmp := dateResultList->head with null    
                                        while (dateTmp != null) {    
                                            let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                            if dateRes->isStart {    
                                                call AvailSearch(accom.F_accom_no, baseDate, dateRes)    
                                            }    
                                            dateTmp := dateTmp->next    
                                        }    
                                    }    
                                    tmp := tmp->next    
                                }    
                            } else {    
                                let dateTmp := dateResultList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart and dateRes->isValid {    
                                        let baseResultList := dateRes->baseResultList    
                                        let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                                        while baseTmp != null {    
                                            let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                            if baseResult->isValid {    
                                                let tmp := clubBases->head with null    
                                                while (tmp != null) {    
                                                    let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                                    if gl_company_no = baseDate->companyNo and    
                                                       baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                                        if baseDate->roomList = null {    
                                                            baseDate->roomList := empty(accomres.RoomList)    
                                                        }    
                                                        call AvailSearch(accom.F_accom_no, baseDate, dateRes)    
                                                    }    
                                                    tmp := tmp->next    
                                                }    
                                            }    
                                            baseTmp := baseTmp->next    
                                        }    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            }    
                        }    
                    }    
                }    
    
    
                let compArr := Companies(clubBases)    
                let compCnt := 1    
                while compArr[compCnt] != "" {    
                    gl_company_no := compArr[compCnt]    
                    if clubCat = 0 {    
                        quick select as catAccTu from cat_acc index F_key    
                        where cat_acc.F_product = clubProduct    
                        and cat_acc.F_company_no = gl_company_no    
                        order by cat_acc.F_category,cat_acc.F_sort_by    
                        on ex.lock {
    
                            --call myerror("One or more cat_acc records skipped",0)    
                            accept    
                        }
    
                        {    
                            call AccomSearch()    
                        }    
                    } else {    
                        quick select as catAccTu from cat_acc index F_key    
                        where cat_acc.F_product = clubProduct    
                        and cat_acc.F_company_no = gl_company_no    
                        and cat_acc.F_category = clubCat    
                        order by cat_acc.F_category,cat_acc.F_sort_by    
                        on ex.lock {
    
                            --call myerror("One or more cat_acc records skipped",0)    
                            accept    
                        }
    
                        {    
                            call AccomSearch()    
                        }    
                    }    
                    compCnt := compCnt + 1    
                }    
            }
    
        }
    
    
        -- Go this route if there is only one base as well.    
        if clubBases->ElementCount() = 1 or    
           (clubCat = 0 and clubType = "*") {    
            if dateResultList = null or dateResultList->IsEmpty() {    
                let tmp := clubBases->head with null    
                while (tmp != null) {    
                    let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                    if baseDate->roomList = null {    
                        baseDate->roomList := empty(accomres.RoomList)    
                    }    
                    gl_company_no := baseDate->companyNo    
                    call SearchByAvail(baseDate->baseCode, baseDate, null)    
                    tmp := tmp->next    
                }    
            } else {    
                if holidayType = holtype.YachtClub {    
                    -- TODO filter out end bases where start base is unavailable    
                    let tmp := clubBases->head with null    
                    while (tmp != null) {    
                        let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                        if baseDate->roomList = null {    
                            baseDate->roomList := empty(accomres.RoomList)    
                        }    
                        gl_company_no := baseDate->companyNo    
                        let dateTmp := dateResultList->head with null    
                        while (dateTmp != null) {    
                            let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                            if dateRes->isStart {    
                                call SearchByAvail(baseDate->baseCode, baseDate, dateRes)    
                            }    
                            dateTmp := dateTmp->next    
                        }    
                        tmp := tmp->next    
                    }    
                } else {    
                    let dateTmp := dateResultList->head with null    
                    while (dateTmp != null) {    
                        let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                        if dateRes->isStart and dateRes->isValid {    
                            let baseResultList := dateRes->baseResultList    
                            let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                            while baseTmp != null {    
                                let baseResult := baseResultList->GetBaseResult(baseTmp)    
                                if baseResult->isValid {    
                                    let tmp := clubBases->head with null    
                                    while (tmp != null) {    
                                        let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                        if baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                            if baseDate->roomList = null {    
                                                baseDate->roomList := empty(accomres.RoomList)    
                                            }    
                                            gl_company_no := baseDate->companyNo    
                                            call SearchByAvail(baseDate->baseCode, baseDate, dateRes)    
                                        }    
                                        tmp := tmp->next    
                                    }    
                                }    
                                baseTmp := baseTmp->next    
                            }    
                        }    
                        dateTmp := dateTmp->next    
                    }    
                }    
            }    
        } else {    
            call SearchByCat()    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    BuildResults(    
        baseDate is baseres.BaseDates,    
        roomResult is accomres.RoomResult with null,    
        yachtResult is accomres.YachtResult with null,    
        avbkRes is avbk.AccomResult with null,    
        baseType is baseres.BaseType,    
        avbkDate is avbkdt.DateTime,    
        avbkDuration is avbkdt.Duration,    
        singlesReqd is boolean,    
        roomSpec is accomres.RoomResult with null,    
        yachtSpec is accomres.YachtResult with null    
    )    
    {
    
    
  
        let tmpAccomDate := avbkRes->accomDateList->head with null    
        while tmpAccomDate != null {    
            let accomDate := cast(tmpAccomDate, avbk.AccomDateElement)    
            let dateResult := empty(dateres.DateResult) with null    
            dateResult->startDate := avbkdt.Date(accomDate->startDT)    
            dateResult->travelDuration := avbkDuration    
            tmpAccomDate := tmpAccomDate->next    
            if roomResult != null {    
                call roomResult->SetAdultsOnly(dateResult->startDate, (dateResult->startDate + avbkdt.DurationToDays(avbkDuration) days))    
                if !singlesReqd and roomResult->InvalidMinPax(adultPax + childPax) {    
                    return    
                }    
                if !roomResult->IsSameRoom(roomSpec) or    
                   !roomResult->IsSuitable(adultPax, childPax, infantPax) {    
                    -- If specification of room is not the same as required, then ignore it.    
                    return    
                }    
                if !ResultMatchClubRequests(roomResult)  {    
                    continue <<>>    
                }    
            }    
            if yachtResult != null {    
                call yachtResult->SetPremier(dateResult->startDate)    
                if !singlesReqd and yachtResult->InvalidMinPax(adultPax + childPax) {    
                    return    
                }    
                if !yachtResult->IsSameYacht(yachtSpec) {    
                    -- If specification of yacht is not the same as required, then ignore it.    
                    return    
                }    
                if !ResultMatchYachtRequests(yachtResult)  {    
                    continue <<>>    
                }    
            }    
            let actualDateResult := dateResultList->UniqueOrder(dateResult)    
            actualDateResult->isStart := actualDateResult->isStart or baseDate->isStartBase    
            --let baseResult := actualDateResult->UniqueAppendBase(baseDate->companyNo, baseDate->baseCode, baseDate->endBaseCode, baseType, baseDate->isStartBase, baseDate->isEndBase)    
            let baseResult := actualDateResult->UniqueAppendBase(baseDate->companyNo, accomDate->startBase, accomDate->endBase, baseType, baseDate->isStartBase, baseDate->isEndBase)    
            if baseResult->isValid {    
                if roomResult != null {    
                    let cce := empty(accomres.ClubCategoryElement)    
                    cce->category := roomResult->category    
                    cce->sortBy := roomResult->sortBy    
                    cce->accomType := roomResult->accomType    
                    if isInternet {    
                        call cce->setInetCat(baseResult->startBase,roomResult->accomType,gl_company_no)    
                        call cce->setPriceList(baseResult->startBase,baseResult->endBase,roomResult->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc,adultPax, childPax)    
                    }    
                    let actualCce := baseResult->accommodationList->clubResult->ClubUniqueOrder(cce)    
                    let room := roomResult->Clone()    
                    room->beforeGap := accomDate->bfrGapDur    
                    room->afterGap := accomDate->afrGapDur    
                    room->beforeBase := accomDate->bfrBase    
                    room->afterBase := accomDate->afrBase    
                    room->accomrefNo := accomDate->accomRef    
                    call room->CalculateStatus(baseResult->startBase, baseResult->endBase)    
                    if room->IsValidStatus(minClubStatus) {    
                        if roomResult->relatedRoomList != null {    
                            -- Search the interconnecting rooms to see if any are vacant on the specificed date.    
                            let relTmp := roomResult->relatedRoomList->head with null    
                            while relTmp != null {    
                                let relRoom := roomResult->relatedRoomList->GetRoomResult(relTmp)    
--display "Rel room", relRoom->accomNo, relRoom->name, avbkdt.Date(accomDate->startDT), avbkdt.DurationToDays(avbkDuration), baseResult->startBase    
                                call relRoom->SetAdultsOnly(dateResult->startDate, (dateResult->startDate + avbkdt.DurationToDays(avbkDuration) days))    
                                let singlesReqd := SinglesReqd(false)    
                                let maxPax := (relRoom->maxSingles if singlesReqd,     
                                            relRoom->maxPax otherwise)    
                                let paxReqd := ((adultPax + childPax) if (SingleAccomReqd(false) &     
                                            singlesReqd), 1 if singlesReqd, null otherwise)    
                                let res := AVBKSearch(relRoom->accomNo, accomDate->startDT, avbkDuration,     
                                        baseResult->startBase, baseResult->endBase, null,    
                                        baseDate->hasDelivery, maxPax, paxReqd) with null    
                                -- hourly    
                                -- ignoreAvail     
                                if res != null and res->accomDateList->elemCount != 0 {    
                                    let relAccomDate := cast(res->accomDateList->head, avbk.AccomDateElement)    
                                    let clonedRelRoom := relRoom->Clone()    
                                    clonedRelRoom->beforeGap := relAccomDate->bfrGapDur    
                                    clonedRelRoom->afterGap := relAccomDate->afrGapDur    
                                    clonedRelRoom->beforeBase := relAccomDate->bfrBase    
                                    clonedRelRoom->afterBase := relAccomDate->afrBase    
                                    call clonedRelRoom->CalculateStatus(baseResult->startBase, baseResult->endBase)    
                                    if clonedRelRoom->IsValidStatus(minClubStatus) {    
                                        if room->relatedRoomList = null {    
                                            room->relatedRoomList := empty(accomres.RoomList)    
                                        }    
                                        call room->relatedRoomList->Append(clonedRelRoom)    
                                    }     
                                }    
                                relTmp := relTmp->next    
                            }    
                        }     
                        if (doInterconnecting = AllRooms or    
                           (doInterconnecting = InterconnectingOnly and (room->relatedRoomList != null and !room->relatedRoomList->IsEmpty())) or    
                           (doInterconnecting = NoInterconnecting and (room->relatedRoomList = null or room->relatedRoomList->IsEmpty())) or    
                           doInterconnecting = StdPlusInterconnecting) {    
                               if (doInterconnecting = AllRooms and    
                               (room->relatedRoomList != null and !room->relatedRoomList->IsEmpty())) and    
                               coalesceAccom {    
                                -- Add the room in on its own, without the interconnecting status    
                                -- Only needed if the rooms are coalesced.    
                                let singleRoom := room->Clone()    
                                call actualCce->AddSameRoomResult(singleRoom)    
                            }    
                            if coalesceAccom {    
                                call room->CoalesceRooms()    
                                if singlesReqd or !room->InvalidMinPax(adultPax + childPax) {    
                                    call actualCce->AddSameRoomResult(room)    
                                }    
                            } else {    
                                call actualCce->AddRoomResult(room)    
                            }    
                            call ClubPromotions(baseResult, baseType, dateResult, cce, room)    
                        }    
                    }    
                }    
                if yachtResult != null {    
                                        findEnd is avbkdt.DateTime    
                                        findEnd := accomDate->startDT + dateResult->travelDuration     
                                        let dz, tz := avbkdt.DateAndTime(findEnd)    
                                        --display dz     
                            --display dateResult->startDate, dateResult->travelDuration    
                    let yce := empty(accomres.YachtCategoryElement)    
                    yce->category := yachtResult->category    
                    yce->sortBy := yachtResult->sortBy    
                    yce->accomType := yachtResult->accomType    
                    call yce->setPriceList(baseResult->startBase,baseResult->endBase,yachtResult->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc, adultPax, childPax)    
                    let actualYce := baseResult->accommodationList->yachtResult->YachtUniqueOrder(yce)    
                    let yacht := yachtResult->Clone()    
                    yacht->beforeGap := accomDate->bfrGapDur    
                    yacht->afterGap := accomDate->afrGapDur    
                    yacht->beforeBase := accomDate->bfrBase    
                    yacht->afterBase := accomDate->afrBase    
                    yacht->accomrefNo := accomDate->accomRef    
                                        if gl_company_no = "5" and dz > 26/10/2009 and dz < 02/11/2009 {    
                                                yacht->afterGap := 0    
                                                }    
                                        let uz, wz := avbkdt.DateAndTime(accomDate->startDT)    
                                        if gl_company_no = "5" and uz > 15/03/2009 and uz < 11/04/2009 {    
                                                yacht->beforeGap := 0    
                                                }    
    
                    call yacht->CalculateStatus(baseResult->startBase, baseResult->endBase)    
                    if yacht->IsValidStatus(minYachtStatus) {    
                          
 
                        if coalesceAccom {    
                            call actualYce->AddSameYachtResult(yacht)    
                        } else {    
                            call actualYce->AddYachtResult(yacht)    
                        }    
                        call YachtPromotions(baseResult, baseType, dateResult, yce, yacht)    
                    }    
                }    
                if baseDate->isStartBase {    
                    -- Count the number of accommodation options for the start date.    
                    resultCount := resultCount + 1    
                }    
            }    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    ClubPromotions(    
        origBaseResult is baseres.BaseResult,    
        baseType is baseres.BaseType,    
        dateResult is dateres.DateResult,    
        cce is accomres.ClubCategoryElement,    
        roomResult is accomres.RoomResult    
    )    
    {
    
        if !doPromotions {    
            return    
        }    
        if roomResult->status = accomres.BlueStatus {    
            let actualDateResult := promotionResultList->dateResultList->UniqueOrder(dateResult->Clone())    
            let baseResult := actualDateResult->UniqueAppendBase(origBaseResult->companyNo, origBaseResult->startBase, origBaseResult->endBase, baseType, origBaseResult->isStartBase, origBaseResult->isEndBase, false)    
            let actualCce := baseResult->accommodationList->clubResult->ClubUniqueOrder(cce->Clone())    
            let room := roomResult->Clone()    
            call actualCce->AddRoomResult(room)    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    YachtPromotions(    
        origBaseResult is baseres.BaseResult,    
        baseType is baseres.BaseType,    
        dateResult is dateres.DateResult,    
        yce is accomres.YachtCategoryElement,    
        yachtResult is accomres.YachtResult with null    
    )    
    {
    
        if !doPromotions {    
            return    
        }    
        if yachtResult->status = accomres.BlueStatus {    
            let actualDateResult := promotionResultList->dateResultList->UniqueOrder(dateResult->Clone())    
            let baseResult := actualDateResult->UniqueAppendBase(origBaseResult->companyNo, origBaseResult->startBase, origBaseResult->endBase, baseType, origBaseResult->isStartBase, origBaseResult->isEndBase, false)    
            let actualYce := baseResult->accommodationList->yachtResult->YachtUniqueOrder(yce->Clone())    
            let yacht := yachtResult->Clone()    
            call yacht->SetPremier(dateResult->startDate)    
            call actualYce->AddYachtResult(yacht)    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    public function Display(indent is number)    
    returns text    
    {
    
        let indStr := disp.Indent(indent)    
        txt is text    
        txt := txt ^ indStr ^ "Request: " ^ description ^ ""    
        indent := indent+1    
        indStr := disp.Indent(indent)    
        txt := txt ^ indStr ^ "company: " ^ company ^ ""    
        txt := txt ^ indStr ^ "startDate: " ^ startDate ^ ""    
        txt := txt ^ indStr ^ "travelTime: " ^ travelTime ^ ""    
        txt := txt ^ indStr ^ "travelDuration: " ^ travelDuration ^ ""    
        txt := txt ^ indStr ^ "leaway: " ^ leaway ^ ""    
        txt := txt ^ indStr ^ "holidayType: " ^ holidayType ^ ""    
        txt := txt ^ indStr ^ "product: " ^ product ^ ""    
        txt := txt ^ indStr ^ "\tclubProduct: " ^ clubProduct ^ ""    
        txt := txt ^ indStr ^ "\tyachtProduct: " ^ yachtProduct ^ ""    
        txt := txt ^ indStr ^ "area: " ^ area ^ ""    
        txt := txt ^ indStr ^ "clubStartBase: " ^ clubStartBase ^ ""    
        txt := txt ^ indStr ^ "yachtStartBase: " ^ yachtStartBase ^ ""    
        txt := txt ^ indStr ^ "yachtEndBase: " ^ yachtEndBase ^ ""    
        txt := txt ^ indStr ^ "adultPax: " ^ adultPax ^ ""    
        txt := txt ^ indStr ^ "childPax: " ^ childPax ^ ""    
        txt := txt ^ indStr ^ "clubCat: " ^ clubCat ^ ""    
        txt := txt ^ indStr ^ "clubType: " ^ clubType ^ ""    
        txt := txt ^ indStr ^ "yachtCat: " ^ yachtCat ^ ""    
        txt := txt ^ indStr ^ "yachtType: " ^ yachtType ^ ""    
        txt := txt ^ indStr ^ "price: " ^ price ^ ""    
        txt := txt ^ indStr ^ "doInterconnecting: " ^ doInterconnecting ^ ""    
        txt := txt ^ indStr ^ "showHeldBookings:" ^ showHeldBookings ^ ""    
        txt := txt ^ indStr ^ "showAvailableBases:" ^ showAvailableBases ^ ""    
        txt := txt ^ indStr ^ "clubBases:"    
        if clubBases != null {    
            txt := txt ^ clubBases->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo club bases"    
        }    
        txt := txt ^ indStr ^ "yachtBases:"    
        if yachtBases != null {    
            txt := txt ^ yachtBases->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo yacht bases"    
        }    
        txt := txt ^ indStr ^ "Flight Requests:"    
        if flightRequests != null {    
            txt := txt ^ flightRequests->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo flight requests"    
        }    
        txt := txt ^ indStr ^ "Accommodation Requests:"    
        if accomRequests != null {    
            txt := txt ^ accomRequests->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo accommodation requests"    
        }    
        return txt    
    }
    
        
    ------------------------------------------------------------------------------------------------------    
    procedure Flights(    
        baseList is baseres.BaseDatesList with null,    
        baseType is baseres.BaseType    
    )    
    {
    
        -- Hash list to ensure that routelink searches are only performed once per airport.    
        if !((gl_company_no = "1" or gl_company_no = "7") and gl_inv_co = "1") {    
            -- flights are not applicable    
            return    
        }    
        let hashinst := empty(schash.Hash)    
        call hashinst->SetHashSize(211)    
    
        function MatchesFlightRequest(    
            route is string    
        ) returns boolean    
        {
    
            if flightRequests = null or flightRequests->airportList = null or    
               flightRequests->airportList->IsEmpty() {    
                return true    
            }
    
            let tmp := flightRequests->airportList->head with null    
            while tmp != null {    
                let airport := flightRequests->airportList->GetAirport(tmp)    
                if route matches airport->airportCode ^ "*" {    
                    return true    
                }
    
                tmp := tmp->next    
            }    
            return false    
        }
    
    
        procedure OutBound(    
            baseDate is baseres.BaseDates,    
            baseType is baseres.BaseType,    
            searchStartDate is date,    
            searchEndDate is date,    
            arrAirport is string,    
            avbkDur is avbkdt.Duration    
        )    
        {
    
            let uniqueEntry, ? := hashinst->UniqueEnter(string(arrAirport^searchStartDate^searchEndDate))    
            if uniqueEntry {    
                dat is date with null    
                actualDateResult is dateres.DateResult with null    
                let rTu := empty(schema.routlink)    
                select as rTu from routlink index F_date    
                where F_route matches "*" ^ arrAirport    
                and searchStartDate <= F_date <= searchEndDate    
                order by F_date,F_time asc    
                {
    
                        
                    on ex.pattern {    
                        accept    
                    }    
                    found is boolean := false    
                    depAirport is string    
                    arrAirport is string    
                    depAirport ^ "-" ^ arrAirport := rTu->F_route    
                    select * from airorigin    
                    where F_code = depAirport    
                    and F_origin = gl_origin    
                    {
    
                        found := true    
                    }
    
                    if found and MatchesFlightRequest(rTu->F_route) {    
                        let stdRoute := empty(flightres.RouteResult)    
                        let starRoute := empty(flightres.RouteResult)    
                        call stdRoute->InitFromRoute(rTu, false, true)    
                        call starRoute->InitFromRoute(rTu, true, true)    
                        select * from routflight    
                        where F_route_no = rTu->F_route_no    
                        {
    
                            if dat != rTu->F_date {    
                                let dateResult := empty(dateres.DateResult) with null    
                                dateResult->startDate := routlink.F_date    
                                dateResult->travelDuration := avbkDur    
                                actualDateResult := dateResultList->UniqueOrder(dateResult)    
                                actualDateResult->isStart := actualDateResult->isStart or baseDate->isStartBase    
                                let baseResult := actualDateResult->UniqueAppendBase(baseDate->companyNo, baseDate->baseCode, baseDate->endBaseCode, baseType, baseDate->isStartBase, baseDate->isEndBase)    
                                dat := rTu->F_date    
                            }    
                            call flightrout.FindFlight(routflight.F_flight_no, flightProduct, travelDuration, arrAirport, adultPax, childPax, doPartial, isInternet, stdRoute, starRoute)    
                        }
    
                        if stdRoute->flightList != null and stdRoute->flightList->elemCount != 0 and    
                           !stdRoute->starClass and (flightRequests = null or !flightRequests->premiumSeats) {    
                            stdRoute := actualDateResult->routeList->UniqueAppend(stdRoute)    
                        }    
--display "starRoute", starRoute->Display(1)    
                        if starRoute->flightList != null and starRoute->flightList->elemCount != 0 and    
                           starRoute->starClass {    
                            starRoute := actualDateResult->routeList->UniqueAppend(starRoute)    
                        }    
                    }    
                }
    
            }    
        }
    
    
        procedure InBound()    
        {
    
            procedure InRoute(    
                outRoute is flightres.RouteResult    
            )    
            {
    
                let rTu := empty(schema.routlink)    
                let depDate := outRoute->arrDate + travelDuration days    
                let route := empty(flightres.RouteResult)    
--display "Search", outRoute->arrAirport ^ '-' ^ outRoute->depAirport, outRoute->depNo, depDate, outRoute->starClass    
                select as rTu from routlink index F_date    
                where F_route = outRoute->arrAirport ^ '-' ^ outRoute->depAirport    
                and F_dep_no = outRoute->depNo    
                and depDate <= F_date <= (depDate + 1 day)    
                order by F_route, F_date,F_time asc    
                {
    
                    select * from routflight    
                    where F_route_no = rTu->F_route_no    
                    order by F_date,F_time asc    
                    {
    
                        call route->InitFromRoute(rTu, outRoute->starClass, false)    
                        if outRoute->starClass {    
                            call flightrout.FindFlight(routflight.F_flight_no, flightProduct, travelDuration, outRoute->depAirport, adultPax, childPax, doPartial, isInternet, null, route)    
                        } else {    
                            call flightrout.FindFlight(routflight.F_flight_no, flightProduct, travelDuration, outRoute->depAirport, adultPax, childPax, doPartial, isInternet, route, null)    
                        }    
                    }
    
                    stop    
                }
    
                outRoute->inBoundRoute := route    
            }
    
        
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                let tmpRoute := dateRes->routeList->head with null    
                while tmpRoute != null {    
                    let outRoute := dateRes->routeList->GetRouteResult(tmpRoute)    
--display outRoute->Display(0)    
                    call InRoute(outRoute)    
                    tmpRoute := tmpRoute->next    
                    if (flightRequests = null or !doPartial) and    
                        !outRoute->IsCompleteRoute() {    
                        ? := dateRes->routeList->ElemDelete(outRoute)    
                    }    
                
                }    
                dateTmp := dateTmp->next    
            }    
        }
    
    
        if baseList != null and (dateResultList = null or dateResultList->IsEmpty()) {    
            let outBoundCount := 0    
            let tmpBase := baseList->head with null    
            while tmpBase != null {    
                let baseDate := baseList->GetBaseDatesList(tmpBase) with null    
                let outBaseTu := cache.GetBase(baseDate->companyNo, baseDate->baseCode)    
                let inBaseTu := cache.GetBase(baseDate->companyNo, baseDate->endBaseCode)    
                let dateRangeList := baseDate->dateRangeList    
                let tmpDate := dateRangeList->head with null    
                while (tmpDate != null) {    
                    let dateRange := dateRangeList->GetDateRange(tmpDate)    
                    let avbkDur := avbkdt.DaysToDuration(baseTravelDur)    
--                    let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                    if baseDate->isStartBase {    
                        call OutBound(baseDate, baseType,     
                            dateRange->startDate, dateRange->endDate,     
                            outBaseTu->F_airport, avbkDur)    
                    }    
                    tmpDate := tmpDate->next    
                }    
                tmpBase := tmpBase->next    
            }    
        } else if dateResultList != null and baseList != null {    
            let outBoundCount := 0    
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                if dateRes->isStart {    
                    let baseResultList := dateRes->baseResultList    
                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                    while baseTmp != null {    
                        let baseResult := baseResultList->GetBaseResult(baseTmp)    
                        if baseResult->isValid {    
                            let outBaseTu := cache.GetBase(baseResult->companyNo, baseResult->startBase)    
                            let inBaseTu := cache.GetBase(baseResult->companyNo, baseResult->endBase)    
                            let tmp := baseList->head with null    
                            while (tmp != null) {    
                                let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                if baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                    --outBoundCount := outBoundCount + OutBound(baseDate, outBaseTu, inBaseTu, dateRes->startDate, dateRes->travelDuration, baseType, 0)    
                                    call OutBound(baseDate, baseType, dateRes->startDate, dateRes->startDate, outBaseTu->F_airport, dateRes->travelDuration)    
                                }    
                                tmp := tmp->next    
                            }    
                        }    
                        baseTmp := baseTmp->next    
                    }    
                }    
                dateTmp := dateTmp->next    
            }    
        }    
        call InBound()    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
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
    
                        let relRoom := accomres.BuildRoomResultFromAccom(tu, room->baseCode, adultPax, childPax, infantPax)    
                        relRoom->relatedRoomType := F_rel_level    
                        relRoom->baseCode := room->baseCode    
                        if room->relatedRoomList = null {    
                            room->relatedRoomList := empty(accomres.RoomList)    
                        }    
                        call room->relatedRoomList->Append(relRoom)    
                    }
    
                }    
            }
    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    proc AddHeldOptions(    
        travelDate is date,    
        travelDur is avbkdt.Duration,    
        baseRes is baseres.BaseResult,    
        clubCategoryElem is accomres.ClubCategoryElement with null,    
        yachtCategoryElem is accomres.YachtCategoryElement with null,    
        room is accomres.RoomResult with null,    
        yacht is accomres.YachtResult with null    
    )    
    {
    
        accomNo is large number    
        if room != null {    
            accomNo := room->accomNo    
        } else {    
            accomNo := yacht->accomNo    
        }    
        singlesReqd is boolean := SinglesReqd(!(baseRes->baseType = baseres.ClubBase))    
        singleAccomReqd is boolean := SingleAccomReqd(!(baseRes->baseType = baseres.ClubBase))    
        maxSingles is small number with null    
        if singlesReqd {    
            let accomTpl := empty(schema.accom)    
            select one as accomTpl from accom    
                where accom.F_accom_no = accomNo {
    
            }
    
            ?, maxSingles := pub.GetMaxPax(gl_company_no, accomTpl, null)    
        }    
        let rqt := empty(avbk.Request)    
        call rqt->Init(    
            accomNo,    
            avbkdt.DateToMidday(travelDate),    
            travelDur,    
            null,    
            baseRes->startBase,    
            baseRes->endBase,    
            false,    
            null,    
            (null if !singlesReqd, (adultPax + childPax) if singleAccomReqd, 1 otherwise),    
            null,    
            maxSingles,    
            false,    
            true)    
    
        let bkgResultList := empty(avbk.Controller)->FindBookings(rqt)    
        if !bkgResultList->IsEmpty() {    
            let bkgPtr := cast(bkgResultList->head, avbk.BookResult) with null    
            while bkgPtr != null {    
                heldBooking is boolean := false    
                if bkgPtr->singlesPax = null {    
                    if book.book_status(bkgPtr->clientNo) = "H" {    
                        if clubCategoryElem != null {    
                            let heldResult := empty(accomres.HeldRoomResult)    
                            call heldResult->InitFromRoom(room)    
                            heldResult->accomNo := accomNo    
                            heldResult->baseCode := baseRes->startBase    
                            heldResult->clientNo := bkgPtr->clientNo    
                            heldResult->accomrefNo := bkgPtr->accomRef    
                            heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                            heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                            heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                            heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                            heldResult->singlesPax := bkgPtr->singlesPax    
                            heldResult->maxSingles := bkgPtr->maxSingles    
                            if room->relatedRoomList != null {    
                                -- Search the interconnecting rooms to see if any are held    
                                if heldResult->relatedRoomList = null {    
                                    heldResult->relatedRoomList := empty(accomres.RoomList)    
                                }    
                                let relTmp := room->relatedRoomList->head with null    
                                while relTmp != null {    
                                    let relRoom := room->relatedRoomList->GetRoomResult(relTmp)    
                                    let rqt := empty(avbk.Request)    
                                    call rqt->Init(    
                                        relRoom->accomNo,    
                                        avbkdt.DateToMidday(travelDate),    
                                        travelDur,    
                                        null,    
                                        baseRes->startBase,    
                                        baseRes->endBase,    
                                        false,    
                                        null,    
                                        (null if !singlesReqd, (adultPax + childPax) if singleAccomReqd, 1 otherwise),    
                                        null,    
                                        maxSingles,    
                                        false,    
                                        true)    
        
                                    let relBkgResultList := empty(avbk.Controller)->FindBookings(rqt)    
                                    if !relBkgResultList->IsEmpty() {    
                                        let relBkgPtr := cast(relBkgResultList->head, avbk.BookResult) with null    
                                        let endDate := avbkdt.Date(relBkgPtr->endDT)    
                                        if book.book_status(relBkgPtr->clientNo) = "H" {    
                                            let relHeldResult := empty(accomres.HeldRoomResult)    
                                            call relHeldResult->InitFromRoom(relRoom)    
                                            relHeldResult->accomNo := relRoom->accomNo    
                                            relHeldResult->baseCode := baseRes->startBase    
                                            relHeldResult->clientNo := relBkgPtr->clientNo    
                                            relHeldResult->accomrefNo := relBkgPtr->accomRef    
                                            relHeldResult->startDate := avbkdt.Date(relBkgPtr->startDT)    
                                            relHeldResult->startTime := avbkdt.TimeOfDay(relBkgPtr->startDT)    
                                            relHeldResult->endDate := avbkdt.Date(relBkgPtr->endDT)    
                                            relHeldResult->endTime := avbkdt.TimeOfDay(relBkgPtr->endDT)    
                                            relHeldResult->singlesPax := relBkgPtr->singlesPax    
                                            relHeldResult->maxSingles := relBkgPtr->maxSingles    
                                            call heldResult->relatedRoomList->Append(relHeldResult)    
                                        }    
                                    } else {    
                                        let clonedRelRoom := relRoom->Clone()    
                                        call heldResult->relatedRoomList->Append(clonedRelRoom)    
                                    }    
                                    relTmp := relTmp->next    
                                }    
    
                            }     
                                
                            let cce := clubCategoryElem->Clone()    
                            let actualCce := baseRes->accommodationList->clubResult->ClubUniqueOrder(cce)    
                            call actualCce->AddHeldRoomResult(heldResult)    
                            actualCce->heldOptCategory := true    
                        } else {    
                            let heldResult := empty(accomres.HeldYachtResult)    
                            heldResult->accomNo := accomNo    
                            heldResult->baseCode := baseRes->startBase    
                            heldResult->clientNo := bkgPtr->clientNo    
                            heldResult->accomrefNo := bkgPtr->accomRef    
                            heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                            heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                            heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                            heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                            heldResult->singlesPax := bkgPtr->singlesPax    
                            heldResult->maxSingles := bkgPtr->maxSingles    
                            call heldResult->InitFromYacht(yacht)    
                                
                            if yachtCategoryElem != null {    
                                let cce := yachtCategoryElem->Clone()    
                                let actualCce := baseRes->accommodationList->yachtResult->YachtUniqueOrder(cce)    
                                call actualCce->AddHeldYachtResult(heldResult)    
                                actualCce->heldOptCategory := true    
                            }    
                        }    
                    }    
                } else {    
                    let sglPtr := cast(bkgPtr->singlesBookResultList->head, avbk.BookResult) with null    
                    while sglPtr != null {    
    
                        if book.book_status(sglPtr->clientNo) = "H" {    
                            if clubCategoryElem != null {    
                                let heldResult := empty(accomres.HeldRoomResult)    
                                heldResult->accomNo := accomNo    
                                heldResult->baseCode := baseRes->startBase    
                                heldResult->clientNo := sglPtr->clientNo    
                                heldResult->accomrefNo := sglPtr->accomRef    
                                heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                                heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                                heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                                heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                                heldResult->singlesPax := sglPtr->singlesPax    
                                heldResult->maxSingles := bkgPtr->maxSingles    
                                call heldResult->InitFromRoom(room)    
    
                                let cce := clubCategoryElem->Clone()    
                                let actualCce := baseRes->accommodationList->clubResult->ClubUniqueOrder(cce)    
                                call actualCce->AddHeldRoomResult(heldResult)    
                                actualCce->heldOptCategory := true    
                            } else {    
                                if yachtCategoryElem != null {    
                                    let heldResult := empty(accomres.HeldYachtResult)    
                                    heldResult->accomNo := accomNo    
                                    heldResult->baseCode := baseRes->startBase    
                                    heldResult->clientNo := sglPtr->clientNo    
                                    heldResult->accomrefNo := sglPtr->accomRef    
                                    heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                                    heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                                    heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                                    heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                                    heldResult->singlesPax := sglPtr->singlesPax    
                                    heldResult->maxSingles := bkgPtr->maxSingles    
                                    call heldResult->InitFromYacht(yacht)    
    
                                    let cce := yachtCategoryElem->Clone()    
                                    let actualCce := baseRes->accommodationList->yachtResult->YachtUniqueOrder(cce)    
                                    call actualCce->AddHeldYachtResult(heldResult)    
                                    actualCce->heldOptCategory := true    
                                }    
                            }    
                        }    
                        sglPtr := cast(sglPtr->next, avbk.BookResult)    
                    }    
                }    
                bkgPtr := cast(bkgPtr->next, avbk.BookResult)    
            }    
        }    
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    procedure CategoryAccommodation(    
        travelDate is date,    
        travelDur is avbkdt.Duration,    
        baseRes is baseres.BaseResult,    
        baseDates is baseres.BaseDates,    
        catElem is accomres.CategoryElement    
    )    
    {
    
        procedure ClubCategoryAccomodation(    
            roomList is accomres.RoomList with null,    
            clubCatElem is accomres.ClubCategoryElement    
        )    
        {
    
            let tmp := (roomList->head if roomList != null, null otherwise) with null    
            while tmp != null {    
                let room := roomList->GetRoomResult(tmp)    
                tmp := tmp->next    
                if room->category = clubCatElem->category and    
                   room->accomType = clubCatElem->accomType {    
                    call AddHeldOptions(travelDate, travelDur, baseRes,     
                        clubCatElem, null, room, null)    
                }    
            }    
        }
        
    
        procedure YachtCategoryAccomodation(    
            yachtList is accomres.YachtList with null,    
            yachtCatElem is accomres.YachtCategoryElement    
        )    
        {
    
            let tmp := (yachtList->head if yachtList != null, null otherwise) with null    
            while tmp != null {    
                let yacht := yachtList->GetYachtResult(tmp)    
                tmp := tmp->next    
                if yacht->category = yachtCatElem->category and    
                   yacht->accomType = yachtCatElem->accomType {    
                    call AddHeldOptions(travelDate, travelDur, baseRes,     
                        null, yachtCatElem, null, yacht)    
                }    
            }    
        }
        
    
        if baseDates->roomList != null and !baseDates->roomList->IsEmpty() {    
            on ex.null {    
                display "CategoryAccommodation - club", catElem->scriptName, catElem->className    
            }    
            let clubCatElem := cast(catElem, accomres.ClubCategoryElement)    
            call ClubCategoryAccomodation(baseDates->roomList, clubCatElem)    
        } else if baseDates->yachtList != null and !baseDates->yachtList->IsEmpty() {    
            on ex.null {    
                display "CategoryAccommodation - yacht", catElem->scriptName, catElem->className    
            }    
            let yachtCatElem := cast(catElem, accomres.YachtCategoryElement)    
            call YachtCategoryAccomodation(baseDates->yachtList, yachtCatElem)    
        }    
                
    }
    
    
    ------------------------------------------------------------------------------------------------------    
    procedure AddHeldBookings()    
    {
    
        proc ProcessCategories(    
            processClubs is boolean,    
            dateRes is dateres.DateResult,    
            baseRes is baseres.BaseResult,    
            baseDates is baseres.BaseDates,    
            catElem is accomres.CategoryElement    
        )    
        {
    
            if processClubs {    
                if baseRes->accommodationList->clubResult = null or     
                    baseRes->accommodationList->clubResult->IsEmpty() or     
                    !baseRes->accommodationList->clubResult->CategoryMatchNotEmpty(catElem)    
                {    
                    call CategoryAccommodation(dateRes->startDate, dateRes->travelDuration,    
                        baseRes, baseDates, catElem)    
                }    
            } else {    
                if baseRes->accommodationList->yachtResult = null or     
                    baseRes->accommodationList->yachtResult->IsEmpty() or     
                    !baseRes->accommodationList->yachtResult->CategoryMatchNotEmpty(catElem)    
                {    
                    call CategoryAccommodation(dateRes->startDate, dateRes->travelDuration,    
                        baseRes, baseDates, catElem)    
                }    
            }    
        }
    
        proc ProcessBaseDates(    
            dateRes is dateres.DateResult,    
            baseRes is baseres.BaseResult    
        )    
        {
    
            if baseRes->baseType = baseres.ClubBase {    
                let baseDates := clubBases->GetBaseResultMatch(baseRes) with null    
                if baseDates != null and baseDates->categoryList != null and     
                    !baseDates->categoryList->IsEmpty()    
                {    
                    let tmpCat := baseDates->categoryList->head with null    
                    while tmpCat != null {    
                        let catElem := baseDates->categoryList->GetCategoryElement(tmpCat)    
                        tmpCat := tmpCat->next    
                        call ProcessCategories(true, dateRes, baseRes, baseDates, catElem)    
                    }    
                }    
            } else {    
                let baseDates := yachtBases->GetBaseResultMatch(baseRes) with null    
                if baseDates != null and baseDates->categoryList != null and     
                    !baseDates->categoryList->IsEmpty()    
                {    
                    let tmpCat := baseDates->categoryList->head with null    
                    while tmpCat != null {    
                        let catElem := baseDates->categoryList->GetCategoryElement(tmpCat)    
                        tmpCat := tmpCat->next    
                        call ProcessCategories(false, dateRes, baseRes, baseDates, catElem)    
                    }    
                }    
            }    
        }
    
        proc ProcessBases(dateRes is dateres.DateResult)    
        {
    
            let baseResList := dateRes->baseResultList with null    
            if baseResList != null and !baseResList->IsEmpty() {    
                let tmpBaseRes := baseResList->head with null    
                while tmpBaseRes != null {    
                    let baseRes := baseResList->GetBaseResult(tmpBaseRes)    
                    tmpBaseRes := tmpBaseRes->next    
                    call ProcessBaseDates(dateRes, baseRes)    
                }    
            }    
        }
    
        if dateResultList != null and !dateResultList->IsEmpty() {    
            let tmpDateRes := dateResultList->head with null    
            while tmpDateRes != null {    
                let dateRes := dateResultList->GetDateResult(tmpDateRes)    
                tmpDateRes := tmpDateRes->next    
                call ProcessBases(dateRes)    
            }    
        }    
    }
        
}
    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
--------end of Request class def ---------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
        
public function BuildRequest(    
    startDate is date,    
    travelDuration is number,    
    leaway is number,    
    holidayTypeCode is number,    
    product is string,    
    area is string,    
    clubStartBase is string with null,    
    yachtStartBase is string with null,    
    yachtEndBase is string with null,    
    adultPax is number,    
    childPax is number,    
    clubCat is number,    
    clubType is string,    
    yachtCat is number,    
    yachtType is string,    
    sourceVal is string,    
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
    
        
function Companies(    
    baseList is baseres.BaseDatesList with null    
)    
returns array of string    
{
    
    companyArr is array[numberOfCompanies] of string    
    for i = 1 to numberOfCompanies {    
        companyArr[i] := ""    
    }    
    let compCnt := 0    
    if baseList != null {    
        let tmpBase := baseList->head with null    
        while tmpBase != null {    
            let baseDate := baseList->GetBaseDatesList(tmpBase) with null    
            let found := false    
            for j = 1 to compCnt {    
                if baseDate->companyNo = companyArr[j] {    
                    found := true    
                    break <<>>    
                }    
            }    
            if !found {    
                compCnt := compCnt + 1    
                companyArr[compCnt] := baseDate->companyNo    
            }    
            tmpBase := tmpBase->next    
        }    
    }    
    return companyArr    
}
'''

out_req='''constant numberOfCompanies = 5    
    
public type InterconnectingSearch is number    
public constant AllRooms = 0    
public constant InterconnectingOnly = 1    
public constant NoInterconnecting = 2    
public constant StdPlusInterconnecting = 3    
    
public type PriceRange is number    
public constant PriceRange1000 = 1    
public constant PriceRange2000 = 2    
public constant PriceRange3000 = 3    
public constant MaxPriceRange = 3 -- used for range checking    
    
public class RestrictedAccomList is public linkedlist.List    
{



    
    fullList is boolean    
}

    
    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
-------Request class def starts here ---------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
    
public class Request is    
{



    
    description is string    
    company is string    
    startDate is date    
    travelTime is fixed prec 2    
    travelDuration is number    
    leaway is number    
    holidayTypeCode is number    
    product is string    
    area is string    
    clubStartBase is string with null    
    yachtStartBase is string with null    
    yachtEndBase is string with null    
     showAnyYachtEndBase is boolean with null     
    adultPax is number    
    childPax is number    
    infantPax is number    
    clubCat is number    
    clubType is string    
    yachtCat is number    
    yachtType is string    
    yachtAccomNo is large number
    isInternet is boolean    
    price is PriceRange    
    partyClientNo is large number with null    
    sourceValue is string    
    noType is basket.BasketNumberType    
    searchNo is large number    
    yachtExtraType is string with null    
    coalesceAccom is boolean    
    doPromotions is boolean    
    baseTravelDur is number    
    reqDateRange is baseres.DateRange    
    showHeldBookings is boolean    
    showAvailableBases is boolean    
    restrictedBases is linkedlist.List with null    
    restrictedBasesHash is schash.Hash with null    
    checkExpectedPax is boolean with null -- variable to check if the expected pax of boat falls within range for leboat only    
    extrasRequired is boolean with null
    
    private minYachtStatus is accomres.Status with null    
    private minClubStatus is accomres.Status with null    
    private checkValid is boolean -- If set remove invalid dates from output    
    
    private resultCount is number    
    private doInterconnecting is InterconnectingSearch with null    
    private doPartial is boolean    
    --private    
    clubProduct is string    
    yachtProduct is string    
    holidayType is holtype.HolidayType    
    private flightProduct is string    
    private package is string    
    
    extraOptions is extrareq.ExtrasRequest with null    
    flightRequests is flightreq.FlightsRequest with null    
    accomRequests is accomreq.Accommodation with null    
    clubBases is baseres.BaseDatesList with null    
    yachtBases is baseres.BaseDatesList with null    
    dateResultList is dateres.DateResultList with null    
    promotionResultList is promores.PromotionDateResultList with null    
    closedBaseList is baseres.ClosedBaseList with null    
    baseLinkList is baseres.BaseLinkList with null    
    
        
    --------------------------------------------------------------------------------------------------------------------------    
    proc PopulateFromXML(inNode is xmlnodes.BaseNode)    
    {
call debug.DebugNL(("req.v : 106 : p Request->PopulateFromXML [<>]","_"))

    
        holidayTypeCode := inNode->FindNumberElement("holiday_type")    
        company := gl_company_no    
        startDate := inNode->FindDateElement("travel_date")    
        travelDuration := inNode->FindNumberElement("duration")    
        leaway := inNode->FindNumberElement("leeway", 0)    
        reqDateRange := empty(baseres.DateRange)    
        reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
        reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
        product := inNode->FindStringElement("product", "")    
        area := inNode->FindStringElement("area", "")    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
call debug.DebugNL(("req.v : 122 : Request->PopulateFromXML.holtype select <>",""))

    
             holidayType := F_holiday_type    
        }

    
        clubStartBase := ""    
        yachtStartBase := ""    
        yachtEndBase := ""    
        let centreList := inNode->FindElement("centre_list") with null    
        if centreList != null    
        {    
            let centre := centreList->FindElement("centre") with null    
            let firstStartBase := centre->FindStringElement("start_base")    
            let cachedBase := cache.GetBase(gl_company_no, firstStartBase)    
                with null    
            if cachedBase = null    
            {    
                raise ex.arg, "Unrecognised base code " ^ firstStartBase    
            }    
            product := cachedBase->F_product    
            area := cachedBase->F_area    
    
            case holidayType {    
            value holtype.Club    
                clubStartBase := firstStartBase    
            value holtype.Yacht, holtype.Waterways    
                yachtStartBase := firstStartBase    
                yachtEndBase := centre->FindStringElement("end_base", "")    
            value holtype.ClubYacht    
                clubStartBase := firstStartBase    
                centre := centre->GetNext()    
                if centre = null    
                {    
                    yachtStartBase := ""    
                    yachtEndBase := ""    
    
                }    
                else    
                {    
                    yachtStartBase := centre->FindStringElement("start_base")    
                    yachtEndBase := centre->FindStringElement("end_base", "")    
                }    
    
            value holtype.YachtClub    
                yachtStartBase := firstStartBase    
                yachtEndBase := centre->FindStringElement("end_base", "")    
                centre := centre->GetNext()    
                if centre = null    
                {    
                    clubStartBase := ""    
    
                }    
                else    
                {    
                    clubStartBase := centre->FindStringElement("start_base")    
                }    
    
            otherwise    
                raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
            }    
        }    
        adultPax := inNode->FindNumberElement("adult_pax", 0)    
        childPax := inNode->FindNumberElement("child_pax", 0)    
        infantPax := inNode->FindNumberElement("infant_pax", 0)    
    
        if adultPax + childPax = 0    
        {    
            raise ex.arg, "Incorrect pax specified.  Either adultPax or childPax must be greater than 0"    
        }    
    
        clubCat := inNode->FindNumberElement("club_accom_cat", 0)    
        yachtCat := inNode->FindNumberElement("yacht_accom_cat", 0)    
        clubType := inNode->FindStringElement("club_accommodation_type", "")    
        yachtType := inNode->FindStringElement("boat_accommodation_type", "")    
        yachtAccomNo := inNode->FindNumberElement("boat_accommodation_id",0)    
        isInternet := true    
        doPromotions := true    
        coalesceAccom := true    

        extrasRequired := inNode->FindBooleanElement("extras_reqd", true)
    
        let interconnectingReqd :=    
            inNode->FindBooleanElement("interconnecting_reqd", true)    
    
        if interconnectingReqd    
        {    
            if accomRequests = null    
            {    
                accomRequests := empty(accomreq.Accommodation)    
            }    
            if accomRequests->clubRequest = null    
            {    
                accomRequests->clubRequest := empty(accomreq.ClubRequest)    
            }    
            accomRequests->clubRequest->interconnecting := true    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := (StdPlusInterconnecting if accomRequests->clubRequest->interconnecting, NoInterconnecting otherwise)    
            }    
        } else {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := NoInterconnecting    
            }    
        }    
    
        let flightsReqd :=    
            inNode->FindBooleanElement("flights_reqd", false)    
    
        baseTu is schema.base with null    
        case holidayType {    
        value holtype.Club, holtype.ClubYacht    
            if clubStartBase != "" {    
                baseTu := cache.GetBase(gl_company_no, clubStartBase)    
            }    
        value holtype.Yacht, holtype.Waterways, holtype.YachtClub    
            if yachtStartBase != "" {    
                baseTu := cache.GetBase(gl_company_no, yachtStartBase)    
            }    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        if flightsReqd or (baseTu != null and (company = "1" or company = "7") and gl_inv_co = "1" and !pub.CanExFlights(baseTu->F_base_code, isInternet))    
        {    
            if flightRequests = null    
            {    
                flightRequests := empty(flightreq.FlightsRequest)    
            }    
            flightRequests->required := true    
            flightRequests->findPartial := false    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
        -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    
        -- If this is IWW, then search for all bases, one ways and round trips.    
        if company in ("4", "5") {    
            showAvailableBases := true    
        }    
    }

    
        
    --------------------------------------------------------------------------------------------------------------------------    
    proc PopulateFromBookXML(    
        inNode is bsbook.In,    
        adltsPax is number,    
        kidsPax is number,    
        infPax is number    
    )    
    {
call debug.DebugNL(("req.v : 288 : p Request->PopulateFromBookXML [<>][<>][<>][<>]","_",adltsPax,kidsPax,infPax))

    
        company := gl_company_no    
        startDate := inNode->holDet->startDate    
        travelDuration := inNode->holDet->holDuration    
        leaway := 0    
        reqDateRange := empty(baseres.DateRange)    
        reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
        reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
        adultPax := adltsPax    
        childPax := kidsPax    
        infantPax := infPax    
        if inNode->boatDet != null {    
            yachtStartBase := inNode->boatDet->startBase    
            yachtEndBase := (inNode->boatDet->startBase if inNode->boatDet->endBase in (null, ""), inNode->boatDet->endBase otherwise)    
            yachtType := inNode->boatDet->accomType    
            yachtAccomNo := inNode->boatDet->accomNo
        }    
        if inNode->roomDet != null {    
            clubStartBase := inNode->roomDet->base    
            clubType := inNode->roomDet->accomType    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
        -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    }

    
        
    --------------------------------------------------------------------------------------------------------------------------    
    proc PopulateFromAccomref (    
        accRefTu is schema.accomref,    
        adltsPax is number,    
        kidsPax is number,    
        infPax is number    
    )    
    {
call debug.DebugNL(("req.v : 336 : p Request->PopulateFromAccomref [<>][<>][<>][<>]","_",adltsPax,kidsPax,infPax))

    
        company := gl_company_no    
        startDate := accRefTu->F_start_date    
        travelDuration := accRefTu->F_duration    
        leaway := 0    
        reqDateRange := empty(baseres.DateRange)    
        reqDateRange->startDate := ((startDate - leaway days) if leaway >= 1, startDate otherwise)    
        reqDateRange->endDate := ((startDate + leaway days) if leaway >= 1, startDate otherwise)    
        adultPax := adltsPax    
        childPax := kidsPax    
        infantPax := infPax    
            
        if pub.GetYachtRoom(accRefTu->F_accom_no) = "Y"    
        {    
                yachtStartBase := accRefTu->F_base_code    
                yachtEndBase := (accRefTu->F_base_code if accRefTu->F_end_base in (null, ""), accRefTu->F_end_base otherwise)    
                    
                -- if this is IWW and a short break we need to use the short break code    
                if gl_company_no = "5" and travelDuration < 7    
                {    
                        yachtStartBase := "SB" ^ yachtStartBase    
                        yachtEndBase := "SB" ^ yachtEndBase    
                }    
                yachtType := accRefTu->F_acc_type    
            } else {    
                clubStartBase := accRefTu->F_base_code    
                clubType := accRefTu->F_acc_type    
        }    
            
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
         -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    }

    
        
    --------------------------------------------------------------------------------------------------------------------------    
    -- What special offer codes do we need? How are these going to be supported? See ravail.IsOfferType    
    -- What agent information do we need?    
    
    public procedure SetExtraOptions(    
        extras is extrareq.ExtrasRequest    
    )    
    {
call debug.DebugNL(("req.v : 393 : p Request->SetExtraOptions [<>]","_"))

    
        extraOptions := extras    
    }

    
    --------------------------------------------------------------------------------------------------------------------------    
    
    public function SingleAccomReqd(yachtRequest is boolean) returns boolean    
    {
call debug.DebugNL(("req.v : 404 : f Request->SingleAccomReqd [<>]",yachtRequest))

    
        singleAccom is boolean := false    
        if yachtRequest {    
            if (accomRequests != null and (accomRequests->yachtRequest != null or     
                accomRequests->waterwaysRequest != null))    
            {    
                if (holidayType = holtype.Waterways)    
                {    
                    if (accomRequests->waterwaysRequest != null) {    
                        singleAccom := accomRequests->waterwaysRequest->singleYachtAccom    
                    }    
                } else {    
                    if (accomRequests->yachtRequest != null) {    
                        singleAccom := accomRequests->yachtRequest->singleYachtAccom    
                    }    
                }    
            }    
        } else {    
            if (accomRequests != null and accomRequests->clubRequest != null) {    
                singleAccom := accomRequests->clubRequest->singleClubAccom    
            }    
        }    
call debug.DebugNL(("req.v : 428 : ret Request->SingleAccomReqd <>[<>]","",singleAccom))
        return singleAccom    
    }

    
    ------------------------------------------------------------------------------------------------------    
    public function SinglesReqd(yachtRequest is boolean) returns boolean    
    {
call debug.DebugNL(("req.v : 436 : f Request->SinglesReqd [<>]",yachtRequest))

    
        singlesReqd is boolean := false    
        if yachtRequest {    
            if (accomRequests != null and (accomRequests->yachtRequest != null or     
                accomRequests->waterwaysRequest != null))    
            {    
                if (holidayType = holtype.Waterways)    
                {    
                    if (accomRequests->waterwaysRequest != null) {    
                        singlesReqd := accomRequests->waterwaysRequest->singles    
                    }    
                } else {    
                    if (accomRequests->yachtRequest != null) {    
                        singlesReqd := accomRequests->yachtRequest->singles    
                    }    
                }    
            }    
        } else {    
            if (accomRequests != null and accomRequests->clubRequest != null) {    
                singlesReqd := accomRequests->clubRequest->singles    
            }    
        }    
call debug.DebugNL(("req.v : 460 : ret Request->SinglesReqd <>[<>]","",singlesReqd))
        return singlesReqd    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public function ExtrasSearch(    
        companyNo is string,    
        clientNo is large number    
    ) returns result.Result with null    
    {
call debug.DebugNL(("req.v : 472 : f Request->ExtrasSearch [<>][<>]",companyNo,clientNo))

    
        if clientNo in (0, null) {    
call debug.DebugNL(("req.v : 476 : ret Request->ExtrasSearch <>[<>]","","_"))
            return null    
        }

    
        if isInternet and startDate < today + 2 days {    
            raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
call debug.DebugNL(("req.v : 483 : ret Request->ExtrasSearch <>[<>]","","_"))
            return null    
        }

    
        dateResultList := empty(dateres.DateResultList)    
        call BldExtraDateBases(companyNo, clientNo)    
        if dateResultList->IsEmpty() {    
call debug.DebugNL(("req.v : 491 : ret Request->ExtrasSearch <>[<>]","","_"))
            return null    
        }

    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->extraList := extrares.BuildExtraResult(this)    
call debug.DebugNL(("req.v : 499 : ret Request->ExtrasSearch <>[<>]","","_"))
        return res    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    procedure BldExtraDateBases(    
        companyNo is string,    
        clientNo is large number    
    )    
    {
call debug.DebugNL(("req.v : 511 : p Request->BldExtraDateBases [<>][<>]",companyNo,clientNo))

    
        ------------------------------------------------------------------------------------------------------    
        procedure BldExtraBases(    
            dateResult is dateres.DateResult,    
            companyNo is string,    
            clientNo is large number,    
            startDate is date,    
            dur is number    
        )    
        {
call debug.DebugNL(("req.v : 523 : p Request->BldExtraDateBases.BldExtraBases [<>][<>][<>][<>][<>]","_",companyNo,clientNo,startDate,dur))

    
            select unique baseref.F_client_no, baseref.F_base_code, baseref.F_end_base,    
                baseref.F_start_date, baseref.F_duration    
            from baseref = accomref index F_client_no    
            where baseref.F_client_no = clientNo    
            and !(pub.get_prod(baseref.F_base_code) in ("EXT", "OEXT"))    
            and baseref.F_start_date = startDate    
            and baseref.F_duration = dur    
            {
call debug.DebugNL(("req.v : 534 : Request->BldExtraDateBases.BldExtraBases.accomref select <>",""))

    
                    let baseResult := empty(baseres.BaseResult)    
                baseResult->companyNo := companyNo    
                baseResult->startBase := baseref.F_base_code    
                baseResult->endBase := baseref.F_end_base    
    
                select unique accomref.F_client_no, accomref.F_base_code,     
                    accomref.F_start_date, accomref.F_duration, accomref.F_accom_no    
                from accomref index F_client_no    
                where accomref.F_client_no = clientNo    
                and accomref.F_base_code = baseref.F_base_code    
                and accomref.F_start_date = baseref.F_start_date    
                and accomref.F_duration = baseref.F_duration    
                {
call debug.DebugNL(("req.v : 550 : Request->BldExtraDateBases.BldExtraBases.accomref.accomref select <>",""))

    
                    if pub.GetYachtRoom(accomref.F_accom_no) = "Y" {    
                        baseResult->baseType := baseres.YachtBase    
                    } else {    
                        baseResult->baseType := baseres.ClubBase    
                    }    
                    ? := dateResult->baseResultList->UniqueAppend(baseResult)    
                    stop    
                }

    
            }

    
        }

    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        select unique dateref.F_client_no, dateref.F_start_date, dateref.F_duration    
        from dateref = accomref index F_client_no    
        where dateref.F_client_no = clientNo    
        order by dateref.F_start_date ascending    
        {
call debug.DebugNL(("req.v : 577 : Request->BldExtraDateBases.accomref select <>",""))

    
            let dateResult := empty(dateres.DateResult)    
            dateResult->startDate := dateref.F_start_date    
            dateResult->travelDuration := avbkdt.DaysToDuration(dateref.F_duration)    
    
            call BldExtraBases(dateResult, companyNo, dateref.F_client_no,     
                dateref.F_start_date, dateref.F_duration)    
    
            if (dateResult->baseResultList != null and !dateResult->baseResultList->IsEmpty())    
            {    
                ? := dateResultList->UniqueAppend(dateResult)    
            }    
        }

    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public func XMLBookSearch(    
        roomDet is bsbook.InRoomDetails with null,    
        boatDet is bsbook.InBoatDetails with null    
    ) returns result.Result with null    
    {
call debug.DebugNL(("req.v : 604 : f Request->XMLBookSearch [<>][<>]","_","_"))

    
        ------------------------------------------------------------------------------------------------------    
        procedure Product(base is string)    
        {
call debug.DebugNL(("req.v : 610 : p Request->XMLBookSearch.Product [<>]",base))

    
            let tu := cache.GetBase(gl_company_no, base) with null    
            if tu = null {    
                raise ex.arg, "Invalid company base combination" ^ gl_company_no ^ " " ^ base    
            }    
            area := tu->F_area    
            product := tu->F_product    
        }

    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
    
        call cache.Clear()    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
call debug.DebugNL(("req.v : 629 : ret Request->XMLBookSearch <>[<>]","","_"))
            return null    
        }

    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
call debug.DebugNL(("req.v : 637 : Request->XMLBookSearch.holtype select <>",""))

    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }

    
        case holidayType {    
        value holtype.Club    
            call Product(clubStartBase)    
            -- Nothing to do    
        value holtype.Yacht, holtype.Waterways    
            call Product(yachtStartBase)    
            -- Nothing to do    
        value holtype.ClubYacht    
            travelDuration := 7    
            if boatDet != null    
            {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            } else {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            }    
        value holtype.YachtClub    
            travelDuration := 7    
            if roomDet != null    
            {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            } else {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            }    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        let oldCompanyNo := gl_company_no    
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 683 : ret Request->XMLBookSearch <>[<>]","","_"))
                    return res    
                }

    
call debug.DebugNL(("req.v : 688 : ret Request->XMLBookSearch <>",""))
                return empty(result.Result)    
            }

    
        }    
        dateResultList := empty(dateres.DateResultList)    
        let dateResult := empty(dateres.DateResult) with null    
        dateResult->startDate := startDate    
        dateResult->travelDuration := avbkdt.DaysToDuration(travelDuration)    
        dateResult := dateResultList->UniqueOrder(dateResult)    
        dateResult->isStart := true    
        if clubStartBase in (null, "") {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, yachtStartBase, yachtEndBase, baseres.YachtBase, true, true)    
        } else {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, clubStartBase, clubStartBase, baseres.ClubBase, true, true)    
        }    
        if accomRequests != null and accomRequests->clubRequest != null {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := (StdPlusInterconnecting if accomRequests->clubRequest->interconnecting, NoInterconnecting otherwise)    
            }    
        } else {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := StdPlusInterconnecting    
            }    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
        -- if this is a leboat request we dont want a min status    
                if gl_company_no = "5"    
                {    
                        minYachtStatus := null    
                }    
    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    
        -- We should only be building the accom list for a single base, for either    
        -- boat or club on a single date.    
        case holidayType {    
        value holtype.Club    
            let room := empty(accomres.RoomResult)    
            call BuildClubList(room->BuildRoomFromRoomDetails(roomDet))    
        value holtype.Yacht, holtype.Waterways    
            let yacht := empty(accomres.YachtResult)    
            call BuildYachtList(yacht->BuildYachtFromBoatDetails(boatDet))    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        call dateResultList->SetValid(holidayType)    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
call debug.DebugNL(("req.v : 751 : ret Request->XMLBookSearch <>[<>]","","_"))
        return res    
    }

    
    ------------------------------------------------------------------------------------------------------    
    public func AccomrefBookSearch(    
        accRefTu is schema.accomref    
    ) returns result.Result with null    
    {
call debug.DebugNL(("req.v : 761 : f Request->AccomrefBookSearch [<>]","_"))

    
        ------------------------------------------------------------------------------------------------------    
        procedure Product(base is string)    
        {
call debug.DebugNL(("req.v : 767 : p Request->AccomrefBookSearch.Product [<>]",base))

    
            let tu := cache.GetBase(gl_company_no, base) with null    
            if tu = null {    
                raise ex.arg, "Invalid company base combination" ^ gl_company_no ^ " " ^ base    
            }    
            area := tu->F_area    
            product := tu->F_product    
        }

    
    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        ------------------------------------------------------------------------------------------------------    
        call cache.Clear()    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
call debug.DebugNL(("req.v : 786 : ret Request->AccomrefBookSearch <>[<>]","","_"))
            return null    
        }

    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
call debug.DebugNL(("req.v : 794 : Request->AccomrefBookSearch.holtype select <>",""))

    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }

    
        case holidayType {    
        value holtype.Club    
            call Product(clubStartBase)    
            -- Nothing to do    
        value holtype.Yacht, holtype.Waterways    
            call Product(yachtStartBase)    
            -- Nothing to do    
        value holtype.ClubYacht    
            travelDuration := 7    
            if pub.GetYachtRoom(accRefTu->F_accom_no) = "Y"    
            {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            } else {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            }    
        value holtype.YachtClub    
            travelDuration := 7    
            if pub.GetYachtRoom(accRefTu->F_accom_no) = "R"    
            {    
                holidayType := holtype.Club    
                call Product(clubStartBase)    
            } else {    
                holidayType := holtype.Yacht    
                call Product(yachtStartBase)    
            }    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        let oldCompanyNo := gl_company_no    
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 840 : ret Request->AccomrefBookSearch <>[<>]","","_"))
                    return res    
                }

    
call debug.DebugNL(("req.v : 845 : ret Request->AccomrefBookSearch <>",""))
                return empty(result.Result)    
            }

    
        }    
        dateResultList := empty(dateres.DateResultList)    
        let dateResult := empty(dateres.DateResult) with null    
        dateResult->startDate := startDate    
        dateResult->travelDuration := avbkdt.DaysToDuration(travelDuration)    
        dateResult := dateResultList->UniqueOrder(dateResult)    
        dateResult->isStart := true    
        if clubStartBase in (null, "") {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, yachtStartBase, yachtEndBase, baseres.YachtBase, true, true)    
        } else {    
            let baseResult := dateResult->UniqueAppendBase(gl_company_no, clubStartBase, clubStartBase, baseres.ClubBase, true, true)    
        }    
        if accomRequests != null and accomRequests->clubRequest != null {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := (StdPlusInterconnecting if accomRequests->clubRequest->interconnecting, NoInterconnecting otherwise)    
            }    
        } else {    
            if today + 1 month >= startDate {    
                doInterconnecting := AllRooms    
            } else {    
                doInterconnecting := StdPlusInterconnecting    
            }    
        }    
        if today + 1 month >= startDate {    
            minYachtStatus := accomres.RedStatus    
        } else {    
            minYachtStatus := accomres.AmberStatus    
        }    
    
        -- if this is a leboat request we dont want a min status    
        if gl_company_no = "5"    
        {        
            minYachtStatus := null    
        }    
        minClubStatus := accomres.AmberStatus    
        -- Internet returns valid dates only.    
        checkValid := true    
    
        -- We should only be building the accom list for a single base, for either    
        -- boat or club on a single date.    
        case holidayType {    
        value holtype.Club    
            let room := empty(accomres.RoomResult)    
            call BuildClubList(room->BuildRoomFromAccomref(accRefTu))    
        value holtype.Yacht, holtype.Waterways    
            let yacht := empty(accomres.YachtResult)    
            call BuildYachtList(yacht->BuildYachtFromAccomref(accRefTu))    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        call dateResultList->SetValid(holidayType)    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
call debug.DebugNL(("req.v : 908 : ret Request->AccomrefBookSearch <>[<>]","","_"))
        return res    
    }

    
    ------------------------------------------------------------------------------------------------------    
    public function FlightSearch()    
    returns result.Result with null    
    {
call debug.DebugNL(("req.v : 917 : f Request->FlightSearch [<>]",""))

    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
call debug.DebugNL(("req.v : 922 : ret Request->FlightSearch <>[<>]","","_"))
            return null    
        }

    
        if isInternet and startDate < today + 2 days {    
            raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
call debug.DebugNL(("req.v : 929 : ret Request->FlightSearch <>[<>]","","_"))
            return null    
        }

    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
call debug.DebugNL(("req.v : 937 : Request->FlightSearch.holtype select <>",""))

    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }

    
        let oldCompanyNo := gl_company_no    
        dateResultList := empty(dateres.DateResultList)    
        promotionResultList := empty(promores.PromotionDateResultList)    
        if area = "" {    
            area := "*"    
        }    
        if clubType = "" {    
           clubType := "*"        
        }    
        if yachtType = "" {    
           yachtType := "*"        
        }    
        if clubStartBase = "" {    
            clubStartBase := "*"    
        }    
        if yachtStartBase = "" {    
            yachtStartBase := "*"    
        }    
        call cache.Clear()    
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 971 : ret Request->FlightSearch <>[<>]","","_"))
                    return res    
                }

 else {    
call debug.DebugNL(("req.v : 976 : ret Request->FlightSearch <>",""))
                    return empty(result.Result)    
                }

    
            }    
        }    
        doInterconnecting := AllRooms    
        doPartial := false    
        if holidayType in (holtype.Club, holtype.ClubYacht) {    
            call Flights(clubBases, baseres.ClubBase)    
        } else {    
            call Flights(yachtBases, baseres.YachtBase)    
        }    
        let flightCnt := 0    
        let tmpDate := dateResultList->head with null    
        while (tmpDate != null) {    
            let dateRes := dateResultList->GetDateResult(tmpDate) with null    
            if dateRes->routeList != null {    
                if dateRes->routeList->elemCount != 0 {    
                    flightCnt := flightCnt + dateRes->routeList->elemCount    
                } else {    
                    dateRes->isValid := false    
                }    
            }    
            dateRes->baseResultList := null    
            dateRes->promotionList := null    
            tmpDate := tmpDate->next    
        }    
        if flightCnt = 0 {    
            gl_company_no := oldCompanyNo    
call debug.DebugNL(("req.v : 1007 : ret Request->FlightSearch <>",""))
            return empty(result.Result)    
        }

    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
call debug.DebugNL(("req.v : 1017 : ret Request->FlightSearch <>[<>]","","_"))
        return res    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public function AvailSearch()    
    returns result.Result with null    
    {
call debug.DebugNL(("req.v : 1027 : f Request->AvailSearch [<>]",""))

    
    
        let oldLeeway := leaway    
        on ex.once {    
            raise ex.arg, "Invalid holiday type code :" ^ holidayTypeCode    
call debug.DebugNL(("req.v : 1034 : ret Request->AvailSearch <>[<>]","","_"))
            return null    
        }

    
        if isInternet and startDate < today + 2 days {    
            raise ex.arg, "Invalid start date. Start date cannot be before " ^ today + 2 days    
call debug.DebugNL(("req.v : 1041 : ret Request->AvailSearch <>[<>]","","_"))
            return null    
        }

    
        select one * from holtype    
        where holtype.F_code = holidayTypeCode    
        {
call debug.DebugNL(("req.v : 1049 : Request->AvailSearch.holtype select <>",""))

    
             holidayType := F_holiday_type    
            flightProduct := F_alloc_value    
            package := F_pack_code    
        }

    
        let oldCompanyNo := gl_company_no    
        dateResultList := empty(dateres.DateResultList)    
        promotionResultList := empty(promores.PromotionDateResultList)    
        if area = "" {    
            area := "*"    
        }    
        if clubType = "" {    
           clubType := "*"        
        }    
        if yachtType = "" {    
           yachtType := "*"        
        }    
        if clubStartBase = "" {    
            clubStartBase := "*"    
        }    
        if yachtStartBase = "" {    
            yachtStartBase := "*"    
        }    
        call cache.Clear()    
        call pricecache.Clear()            
        if clubBases = null and yachtBases = null {    
            let rv, msg := BuildBases(reqDateRange)    
            if !rv {    
                if closedBaseList != null and !closedBaseList->IsEmpty() {    
                    let res := empty(result.Result)    
                    res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 1084 : ret Request->AvailSearch <>[<>]","","_"))
                    return res    
                }

 else {    
                    raise ex.arg, msg    
call debug.DebugNL(("req.v : 1090 : ret Request->AvailSearch <>",""))
                    return empty(result.Result)    
                }

    
            }    
                
        }    
    
        if doInterconnecting = null {    
            if accomRequests != null and accomRequests->clubRequest != null {    
                doInterconnecting := (InterconnectingOnly if accomRequests->clubRequest->interconnecting, AllRooms otherwise)    
            } else {    
                 doInterconnecting := AllRooms    
            }    
        }    
    
           if flightRequests != null {    
            if (flightRequests->findPartial) {    
                doPartial := true    
            }    
            if flightRequests->required {    
                if holidayType in (holtype.Club, holtype.ClubYacht) {    
                    call Flights(clubBases, baseres.ClubBase)    
                } else {    
                    call Flights(yachtBases, baseres.YachtBase)    
                }    
                let flightCnt := 0    
                let tmpDate := dateResultList->head with null    
                while (tmpDate != null) {    
                    let dateRes := dateResultList->GetDateResult(tmpDate) with null    
                    if dateRes->routeList != null {    
                        if dateRes->routeList->elemCount != 0 {    
                            let baseResultList := dateRes->baseResultList    
                            let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                            dateRes->isValid := false    
                            while baseTmp != null and !dateRes->isValid {    
                                let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                dateRes->isValid := baseResult->isValid    
                                baseTmp := baseTmp->next    
                            }    
                            if dateRes->isValid {    
                                flightCnt := flightCnt + dateRes->routeList->elemCount    
                            }    
                        } else {    
                            dateRes->isValid := false    
                        }    
                    }    
                    tmpDate := tmpDate->next    
                }    
                if flightCnt = 0 {    
                    gl_company_no := oldCompanyNo    
                    if closedBaseList != null and !closedBaseList->IsEmpty() {    
                        let res := empty(result.Result)    
                        res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 1145 : ret Request->AvailSearch <>[<>]","","_"))
                        return res    
                    }

    
call debug.DebugNL(("req.v : 1150 : ret Request->AvailSearch <>[<>]","","_"))
                    return null    
                }

    
                leaway := 0    
            }    
        }    
        case holidayType {    
        value holtype.Club    
            call BuildClubList()    
        value holtype.Yacht, holtype.Waterways    
            call BuildYachtList()    
        value holtype.ClubYacht    
            call BuildClubList()    
            call BuildYachtList()    
        value holtype.YachtClub    
            call BuildYachtList()    
            call BuildClubList()    
        otherwise    
            raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
--call promotions.Debug(Display(1))    
        if flightRequests = null or !flightRequests->required {    
            if holidayType in (holtype.Club, holtype.ClubYacht) {    
                call Flights(clubBases, baseres.ClubBase)    
            } else {    
                call Flights(yachtBases, baseres.YachtBase)    
            }    
        }    
        if showHeldBookings {    
            call AddHeldBookings()    
        }    
        if checkValid {    
            call dateResultList->SetValid(holidayType)    
        }    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        if extrasRequired != false
        {
            res->extraList := extrares.BuildExtraResult(this)    
        }
        res->promotionList := promotionResultList    
        if gl_istui
        {
            call promoreq.Promotions(this, res)    
        }
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
        leaway := oldLeeway    
call debug.DebugNL(("req.v : 1201 : ret Request->AvailSearch <>[<>]","","_"))
        return res    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public function PrevDates() returns result.Result with null    
    {
call debug.DebugNL(("req.v : 1210 : f Request->PrevDates [<>]",""))

    
        closedBaseList := null    
        dateResultList := null    
        promotionResultList := null    
        reqDateRange->startDate := reqDateRange->startDate - 7 days    
        reqDateRange->endDate := reqDateRange->endDate - 7 days    
        let prevRes := WidenSearch() with null    
        if showHeldBookings {    
            call AddHeldBookings()    
        }    
call debug.DebugNL(("req.v : 1222 : ret Request->PrevDates <>[<>]","","_"))
        return prevRes    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public function NextDates() returns result.Result with null    
    {
call debug.DebugNL(("req.v : 1231 : f Request->NextDates [<>]",""))

    
        closedBaseList := null    
        dateResultList := null    
        promotionResultList := null    
        reqDateRange->startDate := reqDateRange->startDate + 7 days    
        reqDateRange->endDate := reqDateRange->endDate + 7 days    
        let nextRes := WidenSearch() with null    
        if showHeldBookings {    
            call AddHeldBookings()    
        }    
call debug.DebugNL(("req.v : 1243 : ret Request->NextDates <>[<>]","","_"))
        return nextRes    
    }

    
    --------------------------------------------------------------------------------------------------------------------------    
        
    public function WidenSearch()    
    returns result.Result with null    
    {
call debug.DebugNL(("req.v : 1253 : f Request->WidenSearch [<>]",""))

    
        validBases is boolean := false    
        errMsg is string := ""    
        if holidayType in (holtype.Club, holtype.ClubYacht) {    
            if clubBases = null or clubBases->IsEmpty() {    
                clubBases := null    
                yachtBases := null    
                validBases, errMsg := BuildBases(reqDateRange)    
            } else {    
                validBases, errMsg := RebuildBases(reqDateRange)    
            }    
        }    
        if holidayType in (holtype.Yacht, holtype.YachtClub, holtype.Waterways) {    
            if yachtBases = null or yachtBases->IsEmpty() {    
                yachtBases := null    
                clubBases := null    
                validBases, errMsg := BuildBases(reqDateRange)    
            } else {    
                validBases, errMsg := RebuildBases(reqDateRange)    
            }    
        }            
        if !validBases {    
            if closedBaseList != null and !closedBaseList->IsEmpty() {    
                let res := empty(result.Result)    
                res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 1280 : ret Request->WidenSearch <>[<>]","","_"))
                return res    
            }

    
call debug.DebugNL(("req.v : 1285 : ret Request->WidenSearch <>[<>]","","_"))
            return null    
        }

    
        let oldCompanyNo := gl_company_no    
        dateResultList := empty(dateres.DateResultList)    
        promotionResultList := empty(promores.PromotionDateResultList)    
           if flightRequests != null {    
            if (flightRequests->findPartial) {    
                doPartial := true    
            }    
            if flightRequests->required {    
                if holidayType in (holtype.Club, holtype.ClubYacht) {    
                    call Flights(clubBases, baseres.ClubBase)    
                } else {    
                    call Flights(yachtBases, baseres.YachtBase)    
                }    
                let flightCnt := 0    
                let tmpDate := dateResultList->head with null    
                while (tmpDate != null) {    
                    let dateRes := dateResultList->GetDateResult(tmpDate) with null    
                    if dateRes->routeList != null {    
                        if dateRes->routeList->elemCount != 0 {    
                            flightCnt := flightCnt + dateRes->routeList->elemCount    
                        } else {    
                            dateRes->isValid := false    
                        }    
                    }    
                    tmpDate := tmpDate->next    
                }    
                if flightCnt = 0 {    
                    gl_company_no := oldCompanyNo    
                    if closedBaseList != null and !closedBaseList->IsEmpty() {    
                        let res := empty(result.Result)    
                        res->closedBaseList := closedBaseList    
call debug.DebugNL(("req.v : 1321 : ret Request->WidenSearch <>[<>]","","_"))
                        return res    
                    }

    
call debug.DebugNL(("req.v : 1326 : ret Request->WidenSearch <>",""))
                    return empty(result.Result)    
                }

    
                            
            }    
        }    
        case holidayType {    
            value holtype.Club    
                if clubBases = null or !clubBases->ValidAccom() {    
                    call BuildClubList()    
                } else {    
                    call ProcessClubList(clubBases)    
                }    
            value holtype.Yacht, holtype.Waterways    
                if yachtBases = null or !yachtBases->ValidAccom() {    
                    call BuildYachtList()    
                } else {    
                    call ProcessYachtList(yachtBases)    
                }    
            value holtype.ClubYacht    
                if clubBases = null or !clubBases->ValidAccom() {    
                    call BuildClubList()    
                    call BuildYachtList()    
                } else {    
                    call ProcessClubList(clubBases)    
                    call ProcessYachtList(yachtBases)    
                }    
            value holtype.YachtClub    
                if yachtBases = null or !yachtBases->ValidAccom() {    
                    call BuildYachtList()    
                    call BuildClubList()    
                } else {    
                    call ProcessYachtList(yachtBases)    
                    call ProcessClubList(clubBases)    
                }    
            otherwise    
                raise ex.arg, "Invalid value for holidayType :" ^ holidayType    
        }    
        if flightRequests = null or !flightRequests->required {    
            if holidayType in (holtype.Club, holtype.ClubYacht) {    
                call Flights(clubBases, baseres.ClubBase)    
            } else {    
                call Flights(yachtBases, baseres.YachtBase)    
            }    
        }    
        call dateResultList->SetValid(holidayType)    
        let res := empty(result.Result)    
        res->dateList := dateResultList    
        res->closedBaseList := closedBaseList    
        res->extraList := extrares.BuildExtraResult(this)    
        res->promotionList := promotionResultList    
        call promoreq.Promotions(this, res)    
        -- restore the calling company environment.    
        gl_company_no := oldCompanyNo    
call debug.DebugNL(("req.v : 1382 : ret Request->WidenSearch <>[<>]","","_"))
        return res    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public function AlternativeSearch()    
    returns result.Result with null    
    {
call debug.DebugNL(("req.v : 1392 : f Request->AlternativeSearch [<>]",""))

    
        let oldLeeway := leaway    
        let res := AvailSearch() with null    
        if res = null {    
            -- We found nothing, so do the whole search again.    
            if leaway = 0 {    
                leaway := 7    
                reqDateRange->startDate := ((reqDateRange->startDate - leaway days) if leaway >= 1,     
                                reqDateRange->startDate otherwise)    
                reqDateRange->endDate := ((reqDateRange->endDate + leaway days) if leaway >= 1,     
                                reqDateRange->endDate otherwise)    
                if isInternet and reqDateRange->startDate < today + 2 days {    
                    reqDateRange->startDate := today + 2 days    
                }    
                clubBases := null    
                yachtBases := null    
                res := AvailSearch()    
                if res = null or !res->ValidResultSet(this) {    
                    leaway := oldLeeway    
                    if res != null and res->closedBaseList != null and !res->closedBaseList->IsEmpty()    
                    {    
call debug.DebugNL(("req.v : 1415 : ret Request->AlternativeSearch <>[<>]","","_"))
                        return res    
                    }

    
call debug.DebugNL(("req.v : 1420 : ret Request->AlternativeSearch <>[<>]","","_"))
                    return null    
                }

    
            }    
        } else if !res->ValidResultSet(this) {    
            -- We have an accommodation list, so use this again.    
            if leaway = 0 {    
                leaway := 7    
                reqDateRange->startDate := ((reqDateRange->startDate - leaway days) if leaway >= 1,     
                                reqDateRange->startDate otherwise)    
                reqDateRange->endDate := ((reqDateRange->endDate + leaway days) if leaway >= 1,     
                                reqDateRange->endDate otherwise)    
                if isInternet and reqDateRange->startDate < today + 2 days {    
                    reqDateRange->startDate := today + 2 days    
                }    
                res := WidenSearch()    
                if res = null or !res->ValidResultSet(this) {    
                    leaway := oldLeeway    
                    if res != null and res->closedBaseList != null and !res->closedBaseList->IsEmpty()    
                    {    
call debug.DebugNL(("req.v : 1442 : ret Request->AlternativeSearch <>[<>]","","_"))
                        return res    
                    }

    
call debug.DebugNL(("req.v : 1447 : ret Request->AlternativeSearch <>[<>]","","_"))
                    return null    
                }

    
            } else {    
                if res->closedBaseList = null or res->closedBaseList->IsEmpty() {    
                    res := null    
                }    
            }    
        }    
        leaway := oldLeeway    
        call res->SetPrices(null)    
call debug.DebugNL(("req.v : 1460 : ret Request->AlternativeSearch <>[<>]","","_"))
        return res    
    }

    
    --------------------------------------------------------------------------------------------------------------------------    
        -- search criteria used for tui and now leboat web and new avail also    
    public function TuiGSearch(retRoute is boolean with null)    
    returns result.Result with null    
    {
call debug.DebugNL(("req.v : 1470 : f Request->TuiGSearch [<>]","_"))

    
        let oldLeeway := leaway    
            
        let msg := ('Checking Expected Pax')    
        call liberrmsg.LogError('avail',msg)    
            
        let res := empty(result.Result) with null    
        checkExpectedPax := true    
        res := AvailSearch()     
            
        --if res is null then check results for max pax values Leboat web only    
            if (res = null or not(res->ValidResultSet(this))) and !gl_istui    
            {    
                    let msg := ('Checking Max Pax')    
            call liberrmsg.LogError('avail',msg)    
                
                checkExpectedPax := false    
                    res := AvailSearch()    
                        
                    if res != null and res->ValidResultSet(this) {    
                call res->SetPrices(null)    
call debug.DebugNL(("req.v : 1493 : ret Request->TuiGSearch <>[<>]","","_"))
                return res    
            }

    
                
            checkExpectedPax := true    
        }    
            
        if res = null or not(res->ValidResultSet(this)) {    
            -- We found nothing, so do the whole search again. starting from the day    
            -- before the initial start date then moving one day backwards and forwards    
            -- each iteration up to a max of 4 days either side    
    
                        let msg := ('Checking Alternative dates')    
            call liberrmsg.LogError('avail',msg)    
                            
            let goingLeft := true    
            let jump := 0    
            repeat {    
    
                jump := abs(jump) + 1    
                if goingLeft {    
                    jump := jump * -1    
                    goingLeft := false    
                } else {    
                    goingLeft := true    
                }    
    
                reqDateRange->startDate := reqDateRange->startDate + jump days    
                reqDateRange->endDate := reqDateRange->endDate + jump days    
    
                if isInternet and reqDateRange->startDate < today + 2 days {    
                    reqDateRange->startDate := today + 2 days    
                }    
                clubBases := null    
                yachtBases := null    
                    
                let msg := ('Checking Expected Pax')    
                        call liberrmsg.LogError('avail',msg)    
    
                res := AvailSearch()    
                    
                --if res is null then check results for max pax values leboat web only    
                        if (res = null or not(res->ValidResultSet(this))) and !gl_istui    
                        {    
                                checkExpectedPax := false    
                                    
                                let msg := ('Checking Max Pax')    
                            call liberrmsg.LogError('avail',msg)    
                
                                res := AvailSearch()    
                                    
                                if res != null and res->ValidResultSet(this) {    
                            call res->SetPrices(null)    
call debug.DebugNL(("req.v : 1548 : ret Request->TuiGSearch <>[<>]","","_"))
                            return res    
                        }

    
                            
                        checkExpectedPax := true    
                        }    
    
                if res != null and res->ValidResultSet(this) {    
                    call res->SetPrices(null)    
call debug.DebugNL(("req.v : 1559 : ret Request->TuiGSearch <>[<>]","","_"))
                    return res    
                }

    
            } until abs(jump) >= 8    
                
            -- if res is still null then set start bases and end bases to the other way round and call the TuiGSearch again    
                    
        }    
        leaway := oldLeeway    
        call res->SetPrices(null)    
call debug.DebugNL(("req.v : 1571 : ret Request->TuiGSearch <>[<>]","","_"))
        return res    
        
    }

    
    
    --------------------------------------------------------------------------------------------------------------------------    
    procedure ProcessClubList(    
        baseList is baseres.BaseDatesList with null    
    )    
    {
call debug.DebugNL(("req.v : 1583 : p Request->ProcessClubList [<>]","_"))

    
        if baseList = null {    
call debug.DebugNL(("req.v : 1587 : ret Request->ProcessClubList <>",""))
            return    
        }    
        if dateResultList = null or dateResultList->IsEmpty() {    
            let tmpBase := baseList->head with null    
            while (tmpBase != null) {    
                let baseDate := baseList->GetBaseDatesList(tmpBase)     
                let dateRangeList := baseDate->dateRangeList    
                let tmpDate := dateRangeList->head with null    
                while (tmpDate != null) {    
                    let dateRange := dateRangeList->GetDateRange(tmpDate)    
                    let avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                    let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                    let avbkDateRange := empty(avbkdt.DateTimeRange)->Init((dateRange->startDate - leaway days), (dateRange->startDate + leaway days))    
                    gl_company_no := baseDate->companyNo    
                    let roomList := baseDate->roomList with null    
                    let tmpRoom := (roomList->head if roomList != null, null otherwise) with null    
                    while (tmpRoom != null) {    
                        let room := roomList->GetRoomResult(tmpRoom)    
                        call RoomAvailability(null, baseDate->baseCode, baseDate, null, room)    
                        tmpRoom := tmpRoom->next    
                    }    
                    tmpDate := tmpDate->next    
                }    
                tmpBase := tmpBase->next    
            }    
        } else {    
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                if dateRes->isStart and dateRes->isValid {    
                    let baseResultList := dateRes->baseResultList    
                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                    while baseTmp != null {    
                        let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                        if baseResult->isValid {    
                            let tmp := (clubBases->head if clubBases != null, null otherwise) with null    
                            while (tmp != null) {    
                                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                if baseres.BaseResultEqualBaseDate(baseResult, baseDate) or     
                                    holidayType = holtype.YachtClub    
                                {    
                                    gl_company_no := baseDate->companyNo    
                                    let roomList := baseDate->roomList with null    
                                    let tmpRoom := (roomList->head     
                                            if roomList != null,     
                                            null otherwise) with null    
                                    while (tmpRoom != null) {    
                                        let room := roomList->GetRoomResult(    
                                                tmpRoom)    
                                        call RoomAvailability(null,     
                                            baseDate->baseCode,     
                                            baseDate, dateRes, room)    
                                        tmpRoom := tmpRoom->next    
                                    }    
                                }    
                                tmp := tmp->next    
                            }    
                        }    
                        baseTmp := baseTmp->next    
                    }    
                }    
                dateTmp := dateTmp->next    
            }    
        }    
    }

    
    
    --------------------------------------------------------------------------------------------------------------------------    
    procedure ProcessYachtList(    
        baseList is baseres.BaseDatesList with null    
    )    
    {
call debug.DebugNL(("req.v : 1661 : p Request->ProcessYachtList [<>]","_"))

    
            
        if baseList = null {    
call debug.DebugNL(("req.v : 1666 : ret Request->ProcessYachtList <>",""))
            return    
        }    
        if dateResultList = null or dateResultList->IsEmpty() {    
            let tmpBase := baseList->head with null    
            while (tmpBase != null) {    
                let baseDate := baseList->GetBaseDatesList(tmpBase)     
                let dateRangeList := baseDate->dateRangeList    
                let tmpDate := dateRangeList->head with null    
                while (tmpDate != null) {    
                    let dateRange := dateRangeList->GetDateRange(tmpDate)    
                    let avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                    let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                    let avbkDateRange := empty(avbkdt.DateTimeRange)->Init((dateRange->startDate - leaway days), (dateRange->startDate + leaway days))    
                    gl_company_no := baseDate->companyNo    
                    let yachtList := baseDate->yachtList with null    
                    let tmpYacht := (yachtList->head if yachtList != null, null otherwise) with null    
                    while (tmpYacht != null) {    
                        let yacht := yachtList->GetYachtResult(tmpYacht)    
                        call YachtAvailability(null, baseDate->baseCode, baseDate, null, yacht)    
                        tmpYacht := tmpYacht->next    
                    }    
                    tmpDate := tmpDate->next    
                }    
                tmpBase := tmpBase->next    
            }    
        } else {    
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                if dateRes->isStart and dateRes->isValid {    
                    let baseResultList := dateRes->baseResultList    
                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                    while baseTmp != null {    
                        let baseResult := baseResultList->GetBaseResult(baseTmp)    
                        let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
                        while (tmp != null) {    
                            let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                            if baseres.BaseResultEqualBaseDate(baseResult, baseDate) or     
                                holidayType = holtype.ClubYacht    
                            {    
                                gl_company_no := baseDate->companyNo    
                                let yachtList := baseDate->yachtList with null    
                                let tmpYacht := (yachtList->head     
                                            if yachtList != null,     
                                            null otherwise) with null    
                                while (tmpYacht != null) {    
                                    let yacht := yachtList->GetYachtResult(    
                                            tmpYacht)    
                                    call YachtAvailability(null,     
                                        baseDate->baseCode, baseDate,     
                                        dateRes, yacht)    
                                    tmpYacht := tmpYacht->next    
                                }    
                            }    
                            tmp := tmp->next    
                        }    
                        baseTmp := baseTmp->next    
                    }    
                }    
                dateTmp := dateTmp->next    
            }    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    function CheckBaseClosures(    
        compNo is string,    
        baseType is baseres.BaseType,    
        startBase is string,    
        endBase is string with null,    
        requestRange is baseres.DateRange    
    ) returns baseres.DateRangeList with null    
    {
call debug.DebugNL(("req.v : 1742 : f Request->CheckBaseClosures [<>][<>][<>][<>][<>]",compNo,"_",startBase,"_","_"))

    
        dateRangeList is baseres.DateRangeList with null    
        dateListCnt is number := 1    
        for i = requestRange->startDate to requestRange->endDate {    
            let useStartBase := true    
            let baseClsd, clsdMsg := pub.BaseClosed(compNo, startBase, i, baseTravelDur)    
            if !baseClsd and startBase != endBase and endBase != null {    
                baseClsd, clsdMsg := pub.BaseClosed(compNo, endBase, (i + baseTravelDur days), 0)    
                useStartBase := false    
            }    
            if baseClsd {    
                if dateRangeList != null and !dateRangeList->IsEmpty() and     
                    (dateListCnt = dateRangeList->elemCount)    
                {    
                    dateListCnt := dateListCnt + 1    
                }    
                -- Append the base closure to the list.    
                if closedBaseList = null {    
                    closedBaseList := empty(baseres.ClosedBaseList)    
                }    
                let closedBase := empty(baseres.ClosedBase)    
                closedBase->companyNo := compNo    
                closedBase->baseCode := (startBase if useStartBase, endBase otherwise)    
                closedBase->closureMsg := clsdMsg    
                closedBase->baseType := (baseType if useStartBase, baseres.YachtBase     
                    if holidayType = holtype.Yacht, baseres.Waterways otherwise)    
                ? := closedBaseList->UniqueAppend(closedBase)    
            } else {    
                if (dateRangeList = null or dateListCnt > dateRangeList->elemCount) {    
                    if dateRangeList = null {    
                        dateRangeList := empty(baseres.DateRangeList)    
                    }    
                    let dateRange := empty(baseres.DateRange)    
                    dateRange->startDate := i    
                    dateRange->endDate := i    
                    ? := dateRangeList->UniqueAppend(dateRange)    
                }    
                if dateListCnt = dateRangeList->elemCount {    
                    let tmpDateRange := cast(dateRangeList->tail, baseres.DateRange) with null    
                    if tmpDateRange != null {    
                        tmpDateRange->endDate := i    
                    }    
                }    
            }    
        }    
call debug.DebugNL(("req.v : 1789 : ret Request->CheckBaseClosures <>[<>]","","_"))
        return dateRangeList    
    }

    
    --------------------------------------------------------------------------------------------------------------------------    
    private function RebuildBases(    
        requestRange is baseres.DateRange    
    ) returns (boolean, string)    
    {    
        -- Determine the closed base's type depending on the requested holiday type.    
        baseType is baseres.BaseType    
        case holidayType {    
            value holtype.Club, holtype.ClubYacht    
                baseType := baseres.ClubBase    
            value holtype.Yacht, holtype.YachtClub    
                baseType := baseres.YachtBase    
            value holtype.Waterways    
                baseType := baseres.Waterways    
        }    
        function ProcessBases(    
            reqRange is baseres.DateRange,    
            baseList is baseres.BaseDatesList    
        ) returns baseres.BaseDatesList with null    
        {
call debug.DebugNL(("req.v : 1814 : f Request->ProcessBases [<>][<>]","_","_"))

    
            let tmpBaseDate := baseList->head with null    
            while tmpBaseDate != null {    
                let baseDate := baseList->GetBaseDatesList(tmpBaseDate) with null    
                tmpBaseDate := tmpBaseDate->next    
                baseDate->dateRangeList := CheckBaseClosures(baseDate->companyNo, baseType,     
                    baseDate->baseCode, baseDate->endBaseCode, reqRange)    
            }    
call debug.DebugNL(("req.v : 1824 : ret Request->ProcessBases <>[<>]","","_"))
            return baseList    
        }

    
        if (holidayType = holtype.Club) {    
            clubBases := ProcessBases(requestRange, clubBases)    
            if clubBases = null or !clubBases->OpenBases() {    
                return false, "No club bases available"    
            }    
        } else if (holidayType = holtype.ClubYacht) {    
            clubBases := ProcessBases(requestRange, clubBases)    
            if clubBases = null {    
                return false, "No club bases available"    
            }    
            let tmp := (clubBases->head if clubBases != null, null otherwise) with null    
            while (tmp != null) {    
                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                yachtBases, yachtProduct := LinkedBases(baseres.YachtBase, yachtBases, baseDate,     
                                yachtStartBase, yachtEndBase)    
            }    
            if yachtBases = null {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            } else {    
                let openBases := clubBases->OpenBases() and yachtBases->OpenBases()    
                if !openBases {    
                    return false, "No club/yacht base combinations available"    
                }    
            }    
        } else if (holidayType = holtype.YachtClub) {    
            yachtBases := ProcessBases(requestRange, yachtBases)    
            if yachtBases = null {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            }    
            let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
            while (tmp != null) {    
                let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                clubBases, clubProduct := LinkedBases(baseres.ClubBase, clubBases, baseDate,     
                                clubStartBase, null)    
            }    
            if clubBases = null {    
                -- TO DO need to sort our error codes for web access    
                return false, "No club bases available"    
            } else {    
                let openBases := yachtBases->OpenBases() and clubBases->OpenBases()    
                if !openBases {    
                    return false, "No yacht/club base combinations available"    
                }    
            }    
        } else {    
            yachtBases := ProcessBases(requestRange, yachtBases)    
            yachtProduct := product    
            if yachtBases = null or !yachtBases->OpenBases() {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            }    
        }    
        return true, ""    
    }    
    
    --------------------------------------------------------------------------------------------------------------------------    
    private function BuildBases(    
        requestRange is baseres.DateRange    
    ) returns (boolean, string)    
    {    
        let isStartBase := true    
        let isEndBase := true    
        errMsg is string    
        baseTravelDur := travelDuration    
        if holidayType in (holtype.ClubYacht, holtype.YachtClub) {    
            isEndBase := false -- The second base will be the end base    
            baseTravelDur := baseTravelDur div 2    
        }    
        -- Determine the closed base's type depending on the requested holiday type.    
        baseType is baseres.BaseType    
        case holidayType {    
            value holtype.Club, holtype.ClubYacht    
                baseType := baseres.ClubBase    
            value holtype.Yacht, holtype.YachtClub    
                baseType := baseres.YachtBase    
            value holtype.Waterways    
                baseType := baseres.Waterways    
        }    
    
        --------------------------------------------------------------------------------------------------------------------------    
        function CheckBaseRestrictions(    
            startBase is string,    
            endBase is string with null    
        ) returns boolean    
        {
call debug.DebugNL(("req.v : 1915 : f Request->CheckBaseRestrictions [<>][<>]",startBase,"_"))

    
            --------------------------------------------------------------------------------------------------------------------------    
            function FindRestrictions(    
                startBase is string,    
                endBase is string    
            ) returns boolean    
            {
call debug.DebugNL(("req.v : 1924 : f Request->CheckBaseRestrictions.FindRestrictions [<>][<>]",startBase,endBase))

    
                -- Match restrictions for the combination of startBase base.F_base_code    
                -- add to restiction list if necessary    
                let isRestricted := false    
                select from baserest    
                where F_company_no = gl_company_no    
                and F_start_base = startBase    
                and F_end_base = endBase    
                {
call debug.DebugNL(("req.v : 1935 : Request->CheckBaseRestrictions.FindRestrictions.baserest select <>",""))

    
                    let basePair := empty(avbk.BasePairElement)    
                    basePair->startBase := baserest.F_start_base    
                    basePair->endBase := baserest.F_end_base    
                    if restrictedBases = null {    
                        restrictedBases := empty(linkedlist.List)    
                    }    
                    if F_accom_no = 0 {    
                        call restrictedBases->Append(basePair)    
                        isRestricted := true    
                    } else {    
                        if restrictedBasesHash = null {    
                            restrictedBasesHash := empty(schash.Hash)    
                            call restrictedBasesHash->SetHashSize(211)    
                        }    
                        let ?, cls := restrictedBasesHash->Retrieve(string(F_accom_no)) with null    
                        if cls != null {    
                            let list := cast(cls, RestrictedAccomList)    
                            call list->Append(basePair)    
                        } else {    
                            let list := empty(RestrictedAccomList)    
                            call list->Append(basePair)    
                            ? := restrictedBasesHash->Enter(string(F_accom_no), list)    
                        }    
                    }    
                }

    
                    
                -- We also need to check if the turnaround numbers and berth space are ok    
                -- we need to create a dummy accmref tuple    
                let accrefTpl := empty(schema.accomref)    
                    
                accrefTpl->F_base_code := startBase    
                accrefTpl->F_end_base := endBase    
                --accrefTpl->F_accom_no := accomTu->F_accom_no    
                accrefTpl->F_start_date := requestRange->startDate    
                accrefTpl->F_end_date := requestRange->endDate     
                    
                if !book.check_turn_nos(accrefTpl)    
                {    
call debug.DebugNL(("req.v : 1978 : ret Request->CheckBaseRestrictions.FindRestrictions <>",""))
                    return true -- base is restricted    
                }

    
call debug.DebugNL(("req.v : 1983 : ret Request->CheckBaseRestrictions.FindRestrictions <>[<>]","",isRestricted))
                return isRestricted    
            }

    
            --------------------------------------------------------------------------------------------------------------------------    
            allRestricted is boolean := true    
            if endBase in ("", null) {    
                    
                if showAvailableBases {    
                    select from base    
                    where F_area matches area    
                    and F_product != "OLD"    
                    and F_old_base = false    
                    {
call debug.DebugNL(("req.v : 1998 : Request->CheckBaseRestrictions.base select <>",""))

    
                        -- Match restrictions for the combination of startBase base.F_base_code    
                        -- add to restiction list if necessary    
                        let isRestricted := FindRestrictions(startBase, base.F_base_code)    
                        allRestricted := (allRestricted and isRestricted)    
                        if showAvailableBases and base.F_base_code != startBase {    
                            -- Switch bases around to check for restictions    
                            isRestricted := FindRestrictions(base.F_base_code, startBase)    
                            allRestricted := (allRestricted and isRestricted)    
                        }    
    
                    }

    
                } else {    
                    allRestricted := false    
                }    
            } else {    
                -- Match restrictions for the combination of startBase endBase    
                let isRestricted := FindRestrictions(startBase, endBase)    
                allRestricted := (allRestricted and isRestricted)    
            }    
call debug.DebugNL(("req.v : 2022 : ret Request->CheckBaseRestrictions <>[<>]","",allRestricted))
            return allRestricted     
        }

    
        --------------------------------------------------------------------------------------------------------------------------    
    
        function FindBase(    
            reqRange is baseres.DateRange,    
            startBase is string,    
            endBase is string with null,    
            baseList is baseres.BaseDatesList with null    
        ) returns (baseres.BaseDatesList with null, string with null)    
        {
call debug.DebugNL(("req.v : 2036 : f Request->FindBase [<>][<>][<>][<>]","_",startBase,"_","_"))

    
                        let msg := ""    
                           
            -- TODO what about pub.NoRestrictions ??    
            let tu := empty(schema.base)    
            if baseList = null {    
                 baseList := empty(baseres.BaseDatesList)    
            }    
            if baseLinkList = null {    
                baseLinkList := empty(baseres.BaseLinkList)    
            }    
            if startBase matches "*[\*\|\?]*|$" {    
                select as tu from base    
                where F_base_code matches startBase    
                and F_area matches area    
                and F_product = product    
                and F_company_no = gl_company_no    
                and !F_old_base    
                and (F_max_dur = null or F_max_dur >= baseTravelDur)    
                {
call debug.DebugNL(("req.v : 2058 : Request->FindBase.base select <>",""))

    
                        
                    let actualEndBase := endBase    
                    if endBase in ("", null) and !showAvailableBases {    
                        actualEndBase := tu->F_base_code    
                    }    
                        
                    -- if tui then we want to add all linked bases from the baselink table    
                    if endBase = "ANY"    
                    {    
                        -- need to set showAnyYachtEndBase to true    
                        showAnyYachtEndBase := true    
                            
                        endBase := startBase    
                        actualEndBase := ""    
                    }    
                            
                            
                    let minDur := tu->F_min_dur    
                    if tu->F_base_code != actualEndBase and actualEndBase != null {    
                        let minOneWayDur := pub.GetMinOneWayDur(    
                            tu->F_base_code, actualEndBase) with null    
                        minDur := (minOneWayDur if minOneWayDur != null, minDur otherwise)    
                    }    
                        
                    if baseTravelDur < minDur {    
                            return null, stringid.Error("Duration is less than minimum duration allowed for this trip", gl_lang)    
                    }    
                    if CheckBaseRestrictions(tu->F_base_code, actualEndBase) {    
                        return null, stringid.Error("There is a restriction on this start/end base combination", gl_lang)    
                    }    
                        
                    -- Check for both start and end base closures.    
                    let dateRangeList := CheckBaseClosures(tu->F_company_no, baseType,     
                                tu->F_base_code, actualEndBase, reqRange) with null    
    
                    call baseList->Append(baseres.BuildBaseDates(tu->F_company_no,     
                        tu->F_base_code, actualEndBase, dateRangeList,     
                        isStartBase, isEndBase, F_deliv_reqd))    
                    call cache.EnterBase(tu)    
--<<JB TBD: Determine if we ever get yacht but no club results or club     
-- but no yacht resultswhen doing club/yacht or yacht/club searches.>>    
--                    if !(holidayType in (holtype.ClubYacht, holtype.YachtClub)) {    
                        ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                            tu->F_company_no, tu->F_base_code,     
                            pub.GetExtraBase(tu->F_base_code), null, null))    
--                    }    
                }

    
            } else {    
                -- product must be set    
                -- Add the premier bases to the result list as well.    
                select as tu from base    
                where F_product = product    
                and F_area matches area    
                and F_company_no = gl_company_no    
                and F_base_code = startBase    
                and !F_old_base    
                and (F_max_dur = null or F_max_dur >= baseTravelDur)    
                {
call debug.DebugNL(("req.v : 2121 : Request->FindBase.base select <>",""))

    
                    let actualEndBase := endBase    
                    if endBase in ("", null) and !showAvailableBases {    
                        actualEndBase := tu->F_base_code    
                    }    
                    let minDur := tu->F_min_dur    
                    if tu->F_base_code != actualEndBase and actualEndBase != null {    
                        let minOneWayDur := pub.GetMinOneWayDur(    
                            tu->F_base_code, actualEndBase) with null    
                        minDur := (minOneWayDur if minOneWayDur != null, minDur otherwise)    
                    }    
                    if baseTravelDur < minDur {    
                        reject    
                    }    
                    -- Check for both start and end base closures.    
                    let dateRangeList := CheckBaseClosures(tu->F_company_no, baseType,     
                                tu->F_base_code, actualEndBase, reqRange) with null    
    
                    call cache.EnterBase(tu)    
                    call baseList->Append(baseres.BuildBaseDates(tu->F_company_no,     
                        tu->F_base_code, actualEndBase, dateRangeList,     
                        isStartBase, isEndBase, F_deliv_reqd))    
--<<JB TBD: Determine if we ever get yacht but no club results or club     
-- but no yacht resultswhen doing club/yacht or yacht/club searches.>>    
--                    if !(holidayType in (holtype.ClubYacht, holtype.YachtClub)) {    
                        ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                            tu->F_company_no, tu->F_base_code,     
                            pub.GetExtraBase(tu->F_base_code), null, null))    
--                    }    
                    if (((isInternet and tu->F_pb_internet_use = 'I') or     
                        (!isInternet and tu->F_pb_internet_use = 'N') or     
                        (tu->F_pb_internet_use = 'B')) and tu->F_premier_base != "")    
                    {    
                        -- Check for premier base closures.    
                        let dateRangeList := CheckBaseClosures(tu->F_company_no, baseType,     
                            tu->F_premier_base, actualEndBase, reqRange) with null    
                        call baseList->Append(baseres.BuildBaseDates(    
                            tu->F_company_no, tu->F_premier_base, actualEndBase,     
                            dateRangeList, isStartBase, isEndBase, F_deliv_reqd))    
                    }    
                }

    
            }    
call debug.DebugNL(("req.v : 2167 : ret Request->FindBase <>",""))
            return (null if baseList->IsEmpty(), baseList otherwise), msg    
        }

                
        
        --------------------------------------------------------------------------------------------------------------------------    
        --------------------------------------------------------------------------------------------------------------------------    
        --------------------------------------------------------------------------------------------------------------------------    
        if (holidayType = holtype.Club) {    
            clubBases, errMsg := FindBase(requestRange, clubStartBase, null, clubBases)    
            clubProduct := product    
            if clubBases = null or !clubBases->OpenBases() {    
                if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
        } else if (holidayType = holtype.ClubYacht) {    
            clubBases, errMsg := FindBase(requestRange, clubStartBase, null, clubBases)    
            if clubBases = null {    
                if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
            clubProduct := product    
            let tmp := (clubBases->head if clubBases != null, null otherwise) with null    
            while (tmp != null) {    
                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                yachtBases, yachtProduct := LinkedBases(baseres.YachtBase, yachtBases, baseDate,     
                                yachtStartBase, yachtEndBase)    
            }    
            if yachtBases = null {    
                return false, stringid.Error("No boat bases available", gl_lang)    
            } else {    
                let openBases := clubBases->OpenBases() and yachtBases->OpenBases()    
                if !openBases {    
                    return false, "No club/yacht base combinations available"    
                }    
            }    
        } else if (holidayType = holtype.YachtClub) {    
            yachtBases, errMsg := FindBase(requestRange, yachtStartBase, yachtEndBase, yachtBases)    
            if yachtBases = null {    
                    if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
            yachtProduct := product    
            let tmp := (yachtBases->head if yachtBases != null, null otherwise)with null    
            while (tmp != null) {    
                let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                tmp := tmp->next    
                clubBases, clubProduct := LinkedBases(baseres.ClubBase, clubBases, baseDate,     
                                clubStartBase, null)    
            }    
            if clubBases = null {    
                -- TO DO need to sort our error codes for web access    
                return false, "No club bases available"    
            } else {    
                let openBases := yachtBases->OpenBases() and clubBases->OpenBases()    
                if !openBases {    
                    return false, "No yacht/club base combinations available"    
                }    
            }    
        } else {    
            yachtBases, errMsg := FindBase(requestRange, yachtStartBase, yachtEndBase, yachtBases)    
            yachtProduct := product    
            if yachtBases = null or !yachtBases->OpenBases() {    
                if errMsg = "" {    
                        return false, stringid.Error("No boat bases available", gl_lang)    
                    } else {    
                            return false, errMsg    
                    }    
            }    
        }    
        return true, ""    
    }    
    --------------------------------------------------------------------------------------------------------------------------    
    
    private function AVBKSearch(    
        accomNo is large number,    
        avbkDate is avbkdt.DateTime with null,    
        avbkDur is avbkdt.Duration,    
        fromBase is string,    
        toBase is string with null,    
        dateRange is avbkdt.DateTimeRange with null,    
        hasDelivery is boolean,    
        maxPax is small number,    
        singlesPax is small number with null,    
        hourly is boolean with null,        -- null -> false    
        ignoreAvail is boolean with null    --  ignore avail.f rows/or lack of    
    ) returns avbk.AccomResult with null    
    {    
 
        let rqt := empty(avbk.Request)    
        let baseList := restrictedBases with null    
        if restrictedBasesHash != null {    
            let ?, list := restrictedBasesHash->Retrieve(string(accomNo)) with null    
            if list != null {    
                let accomBaseList := cast(list, RestrictedAccomList) with null    
                if !accomBaseList->fullList {    
                    let tmp := (restrictedBases->head if (restrictedBases != null), null otherwise) with null    
                    while tmp != null {    
                        let basePair := cast(tmp, avbk.BasePairElement)    
                        let newBasePair := empty(avbk.BasePairElement)    
                        newBasePair->startBase := basePair->startBase    
                        newBasePair->endBase := basePair->endBase    
                        call accomBaseList->Append(newBasePair)    
                        tmp := tmp->next    
                    }    
                    accomBaseList->fullList := true    
                }    
                baseList := accomBaseList    
            }    
        }    
        call rqt->Init(    
            accomNo,    
            avbkDate,    
            avbkDur,    
            dateRange,    
            fromBase,    
            (null if showAnyYachtEndBase = true, toBase if (toBase != null or showAvailableBases), fromBase otherwise),    
            (showAvailableBases and yachtStartBase != "*" and showAnyYachtEndBase != true and !gl_istui),    
            baseList,    
            singlesPax,    
            hourly,    
            maxPax,    
            --(maxPax if singlesPax != null, null otherwise),    
            hasDelivery,    
            ignoreAvail)    
            
        let res := empty(avbk.Controller)->FindAccomResult(rqt)    
        --let d, t := avbkdt.DateAndTime(avbkDate)    
--display accomNo, res->accomDateList->elemCount, fromBase, toBase    
        return res    
    }    
    --------------------------------------------------------------------------------------------------------------------------    
            
    private function LinkedBases(    
        baseType is baseres.BaseType,    
        baseList is baseres.BaseDatesList with null,    
        baseDate is baseres.BaseDates,    
        startBase is string,    
        endBase is string with null    
    ) returns (baseres.BaseDatesList with null, string)    
    {    
        let linkedProduct := ""    
        quick select from baselink, base, prodpack    
        where baselink.F_company_no = baseDate->companyNo    
        and baselink.F_first_base = baseDate->baseCode    
        and baselink.F_second_base matches startBase    
        and baselink.F_link_type = baselnk.PrimaryLink    
        and base.F_company_no = baseDate->companyNo    
        and base.F_base_code = baselink.F_second_base    
        and !base.F_old_base    
        and prodpack.F_company_no = baseDate->companyNo    
        and prodpack.F_prod_code = base.F_product    
        and prodpack.F_pack_code matches package    
        order by F_priority    
        {
call debug.DebugNL(("req.v : 2333 : Request->baselink select <>",""))

    
            let actualEndBase := endBase    
            if endBase in ("", null) {    
                actualEndBase := base.F_base_code    
            }    
            if linkedProduct = "" {    
                linkedProduct := base.F_product    
            }    
            if baseDate->dateRangeList != null {    
                let tmpDateRange := baseDate->dateRangeList->head with null    
                while tmpDateRange != null {    
                    let dateRange := baseDate->dateRangeList->GetDateRange(tmpDateRange) with null    
                    tmpDateRange := tmpDateRange->next    
                    let reqRange := empty(baseres.DateRange)    
                    reqRange->startDate := dateRange->startDate + baseTravelDur days    
                    reqRange->endDate := dateRange->endDate + baseTravelDur days    
    
                    -- Check for base closures.    
                    let dateRangeList := CheckBaseClosures(base.F_company_no, baseType,     
                        base.F_base_code, actualEndBase, reqRange) with null    
    
                    if dateRangeList = null or dateRangeList->IsEmpty() {    
                        ? := baseDate->dateRangeList->ElemDelete(dateRange)    
                    } else {    
                        let singleElem := (dateRangeList->elemCount = 1)    
                        let tmpFirstDate := dateRangeList->head with null    
                        if tmpFirstDate != null {    
                            let firstDates := dateRangeList->GetDateRange(    
                                        tmpFirstDate) with null    
                            if firstDates != null {    
                                dateRange->startDate := (firstDates->startDate -     
                                            baseTravelDur days)    
                                if singleElem {    
                                    dateRange->endDate := (firstDates->endDate -     
                                                baseTravelDur days)    
                                }    
                            }    
                        }    
                        if !singleElem {    
                            let tmpLastDates := dateRangeList->tail with null    
                            if tmpLastDates != null {     
                                let lastDates := dateRangeList->GetDateRange(    
                                            tmpLastDates) with null    
                                if lastDates != null {    
                                    dateRange->endDate := (lastDates->endDate -     
                                                baseTravelDur days)    
                                }    
                            }    
                        }    
                        if (baseList = null) {    
                            baseList := empty(baseres.BaseDatesList)    
                        }    
                        let unqBaseDate := baseList->UniqueAppend(baseres.BuildBaseDates(    
                            base.F_company_no, base.F_base_code, actualEndBase,     
                            dateRangeList, false, true, F_deliv_reqd)) with null    
                        unqBaseDate->dateRangeList := dateRangeList    
    
                        ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                            base.F_company_no, baseDate->baseCode,     
                            pub.GetExtraBase(baseDate->baseCode),     
                            actualEndBase, pub.GetExtraBase(actualEndBase)))    
                        -- TODO add schema.base to cache.    
                    }    
                }    
            } else {    
                if (baseList = null) {    
                    baseList := empty(baseres.BaseDatesList)    
                }    
                let unqBaseDate := baseList->UniqueAppend(baseres.BuildBaseDates(    
                    base.F_company_no, base.F_base_code, actualEndBase,     
                    null, false, true, F_deliv_reqd)) with null    
                unqBaseDate->dateRangeList := null    
    
                ? := baseLinkList->UniqueAppend(baseres.BuildBaseLinks(    
                    base.F_company_no, baseDate->baseCode,     
                    pub.GetExtraBase(baseDate->baseCode),     
                    actualEndBase, pub.GetExtraBase(actualEndBase)))    
                -- TODO add schema.base to cache.    
            }    
        }

    
        return (baseList if (baseList != null and !baseList->IsEmpty()), null otherwise), linkedProduct    
    }    
    
    ------------------------------------------------------------------------------------------------------    
    function ResultMatchYachtRequests(    
        yacht is accomres.YachtResult    
    ) returns boolean    
    {
call debug.DebugNL(("req.v : 2425 : f Request->ResultMatchYachtRequests [<>]","_"))

    
        if accomRequests = null or    
           (accomRequests->yachtRequest = null and accomRequests->waterwaysRequest = null) {    
call debug.DebugNL(("req.v : 2430 : ret Request->ResultMatchYachtRequests <>[<>]","",true))
            return true    
        }

    
        if holidayType = holtype.Waterways {    
            let waterwaysRequest := accomRequests->waterwaysRequest    
            if waterwaysRequest->elite and !yacht->isPremier {    
call debug.DebugNL(("req.v : 2438 : ret Request->ResultMatchYachtRequests <>[<>]","",false))
                return false    
            }

    
        } else {    
            let yachtRequest := accomRequests->yachtRequest    
            if yachtRequest->premierYacht and !yacht->isPremier {    
call debug.DebugNL(("req.v : 2446 : ret Request->ResultMatchYachtRequests <>[<>]","",false))
                return false    
            }

    
        }    
call debug.DebugNL(("req.v : 2452 : ret Request->ResultMatchYachtRequests <>[<>]","",true))
        return true    
    }

    
    
    --------------------------------------------------------------------------------------------------------------------------    
    function MatchYachtRequests(    
        yacht is accomres.YachtResult with null,    
        accTypeTu is schema.acc_type    
    ) returns boolean    
    {
call debug.DebugNL(("req.v : 2464 : f Request->MatchYachtRequests [<>][<>]","_","_"))

    
    
        -- Check numbers of pax for TuiG    
        if gl_istui {    
            let totPax := adultPax + childPax    
            if accTypeTu->F_min_sale > totPax or totPax > accTypeTu->F_max_sale {    
call debug.DebugNL(("req.v : 2472 : ret Request->MatchYachtRequests <>[<>]","",false))
                return false    
            }

    
        } 
                
        -- premierYacht status must be checked later when we have the start date.    
        if accomRequests = null or    
           (accomRequests->yachtRequest = null and accomRequests->waterwaysRequest = null) {    
call debug.DebugNL(("req.v : 2482 : ret Request->MatchYachtRequests <>[<>]","",true))
            return true    
        }

    
    
        if holidayType = holtype.Waterways {    
    
            let waterwaysRequest := accomRequests->waterwaysRequest    
            if waterwaysRequest->singleYachtAccom {    
                let totPax := adultPax + childPax    
                if waterwaysRequest->singles {    
                    if totPax > accTypeTu->F_max_singles {    
call debug.DebugNL(("req.v : 2495 : ret Request->MatchYachtRequests <>[<>]","",false))
                        return false    
                    }

    
                } else {    
                    if accTypeTu->F_min_sale > totPax or totPax > accTypeTu->F_max_sale {    
call debug.DebugNL(("req.v : 2502 : ret Request->MatchYachtRequests <>[<>]","",false))
                        return false    
                    }

    
                }    
            }    
            if yacht = null {    
                if waterwaysRequest->cabins > 0 and (accTypeTu->F_fw_cabins + accTypeTu->F_fs_cabins + accTypeTu->F_af_cabins < waterwaysRequest->cabins) {    
call debug.DebugNL(("req.v : 2511 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if waterwaysRequest->heads > 0 and accTypeTu->F_heads < waterwaysRequest->heads {    
call debug.DebugNL(("req.v : 2517 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
            } else {    
                if (waterwaysRequest->cabins > 0 and yacht->numCabins < waterwaysRequest->cabins) or    
                   (waterwaysRequest->heads > 0 and yacht->numHeads < waterwaysRequest->heads) {    
call debug.DebugNL(("req.v : 2525 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if waterwaysRequest->bowThrusters and !yacht->bowThrusters or    
                    waterwaysRequest->airCondition and !yacht->airCondition or    
                    waterwaysRequest->cdCassette and !yacht->cdCassette or    
                    waterwaysRequest->tableChairs and !yacht->tableChairs or    
                    (waterwaysRequest->buildYear > 0 and waterwaysRequest->buildYear > yacht->buildYear) or    
                    (waterwaysRequest->shorePower != "" and waterwaysRequest->shorePower != null     
                    and waterwaysRequest->shorePower != yacht->shorePower) or    
                    (waterwaysRequest->noOfSteerPos != "" and waterwaysRequest->noOfSteerPos != null and    
                    waterwaysRequest->noOfSteerPos != yacht->noOfSteerPos) {    
call debug.DebugNL(("req.v : 2539 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if waterwaysRequest->singles and !yacht->okSingles {    
call debug.DebugNL(("req.v : 2545 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
            }    
        } else {    
            let yachtRequest := accomRequests->yachtRequest    
            if yacht = null {    
                if yachtRequest->cabins > 0 and (accTypeTu->F_fw_cabins + accTypeTu->F_fs_cabins + accTypeTu->F_af_cabins != yachtRequest->cabins) {    
call debug.DebugNL(("req.v : 2555 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if yachtRequest->heads > 0 and accTypeTu->F_heads != yachtRequest->heads {    
call debug.DebugNL(("req.v : 2561 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
            } else {    
                let totPax := adultPax + childPax    
                if yachtRequest->singleYachtAccom {    
                    if yachtRequest->singles {    
                        if totPax > yacht->maxSingles {    
call debug.DebugNL(("req.v : 2571 : ret Request->MatchYachtRequests <>[<>]","",false))
                            return false    
                        }

    
                    } else {    
                        if yacht->minPax > totPax or totPax > yacht->maxPax {    
call debug.DebugNL(("req.v : 2578 : ret Request->MatchYachtRequests <>[<>]","",false))
                            return false    
                        }

    
                    }    
                }    
                if (yachtRequest->cabins > 0 and yacht->numCabins != yachtRequest->cabins) or    
                   (yachtRequest->heads > 0 and yacht->numHeads != yachtRequest->heads) {    
call debug.DebugNL(("req.v : 2587 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if yachtRequest->anchorWinch and !yacht->windlass {    
call debug.DebugNL(("req.v : 2593 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if yachtRequest->autopilot and !yacht->autoPilot {    
call debug.DebugNL(("req.v : 2599 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if yachtRequest->mainSail != "" and yachtRequest->mainSail != null and     
                   yachtRequest->mainSail != yacht->mainSail {    
call debug.DebugNL(("req.v : 2606 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
                if yachtRequest->singles and !yacht->okSingles {    
call debug.DebugNL(("req.v : 2612 : ret Request->MatchYachtRequests <>[<>]","",false))
                    return false    
                }

    
            }    
        }    
call debug.DebugNL(("req.v : 2619 : ret Request->MatchYachtRequests <>[<>]","",true))
        return true    
    }

    
    --------------------------------------------------------------------------------------------------------------------------    
    
    procedure YachtAvailability(    
        yachtSpec is accomres.YachtResult with null,    
        baseCode is string,    
        baseDate is baseres.BaseDates,    
        dateResult is dateres.DateResult with null,    
        yacht is accomres.YachtResult    
    )    
    {
call debug.DebugNL(("req.v : 2634 : p Request->YachtAvailability [<>][<>][<>][<>][<>]","_",baseCode,"_","_","_"))

    
 
        let singlesReqd := SinglesReqd(true)    
        let maxPax := (yacht->maxSingles if singlesReqd, yacht->maxPax otherwise)    
        let paxReqd := ((adultPax + childPax) if (SingleAccomReqd(true) & singlesReqd),     
                1 if singlesReqd, null otherwise)    
            if dateResult = null {    
            let dateRangeList := baseDate->dateRangeList    
            let tmpDate := dateRangeList->head with null    
            while (tmpDate != null) {    
                let dateRange := dateRangeList->GetDateRange(tmpDate)    
                avbkDate is avbkdt.DateTime with null    
                avbkDateRange is avbkdt.DateTimeRange with null    
                if leaway = 0 {    
                    avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                } else {    
                    avbkDateRange := empty(avbkdt.DateTimeRange)->Init(    
                            dateRange->startDate, dateRange->endDate)    
                }    
--                let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)    
                let avbkDur := avbkdt.DaysToDuration(baseTravelDur)    
                    
                let res := AVBKSearch(yacht->accomNo, avbkDate, avbkDur, baseDate->baseCode,     
                        baseDate->endBaseCode, avbkDateRange, baseDate->hasDelivery,     
                        maxPax, paxReqd) with null    
                        -- hourly    
                        -- ignoreAvail     
                call BuildResults(baseDate, null, yacht, res, baseres.YachtBase, avbkDate, avbkDur, singlesReqd, null, yachtSpec)    
                tmpDate := tmpDate->next    
            }    
        } else {    
            let startDate := dateResult->startDate    
            if holidayType = holtype.ClubYacht {    
                startDate := startDate + 7 days    
            }    
            let avbkDate := avbkdt.DateToMidday(startDate)    
            let avbkDur := dateResult->travelDuration    
            let res := AVBKSearch(yacht->accomNo, avbkDate, avbkDur, baseDate->baseCode,     
                    baseDate->endBaseCode, null, baseDate->hasDelivery,     
                    maxPax, paxReqd) with null    
                    -- hourly    
                    -- ignoreAvail     
            call BuildResults(baseDate, null, yacht, res, baseres.YachtBase, avbkDate, avbkDur, singlesReqd)    
        }    
    }

    
    
    --------------------------------------------------------------------------------------------------------------------------    
    public procedure BuildYachtList(    
        yachtSpec is accomres.YachtResult with null    
    )    
    {
call debug.DebugNL(("req.v : 2689 : p Request->BuildYachtList [<>]","_"))

    
        let accTypeTu := empty(schema.acc_type)    
        let accomTu := empty(schema.accom)    
        let catTypeTu := empty(schema.cat_type)    
    
        if yachtBases = null or yachtBases->IsEmpty() {    
call debug.DebugNL(("req.v : 2697 : ret Request->BuildYachtList <>",""))
            return    
        }    
            
        -----------------------------------------------------------------------------    
        procedure ProcessYacht(    
            baseCode is string,    
            baseDate is baseres.BaseDates,    
            dateResult is dateres.DateResult with null    
        )    
        {
call debug.DebugNL(("req.v : 2708 : p Request->BuildYachtList.ProcessYacht [<>][<>][<>]",baseCode,"_","_"))

    
  
            let yacht := accomres.BuildYachtResultFromAccom(accomTu, accTypeTu, holidayType)    
            yacht->category := catTypeTu->F_category    
            yacht->sortBy := catTypeTu->F_sort_by    
            yacht->accomType := accomTu->F_type    
            if !MatchYachtRequests(yacht, accTypeTu) {    
call debug.DebugNL(("req.v : 2717 : ret Request->BuildYachtList.ProcessYacht <>",""))
                return    
            }    
                
            if yachtSpec != null and dateResult != null {    
                call yacht->SetPremier(dateResult->startDate)    
                if !yacht->IsSameYacht(yachtSpec) {    
                    -- If specification of yacht is not the same as required, then ignore it.    
call debug.DebugNL(("req.v : 2725 : ret Request->BuildYachtList.ProcessYacht <>",""))
                    return    
                }    
            }    
            call baseDate->yachtList->Append(yacht)    
            if showHeldBookings {    
                if baseDate->categoryList = null {    
                    baseDate->categoryList := empty(accomres.CategoryList)    
                }    
                let cce := empty(accomres.YachtCategoryElement)    
                cce->category := yacht->category    
                cce->sortBy := yacht->sortBy    
                cce->accomType := yacht->accomType    
                if dateResult != null    
                {    
                    call cce->setPriceList(baseCode,baseDate->endBaseCode,yacht->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc, adultPax, childPax)    
                }    
                ? := baseDate->categoryList->YachtUniqueAppend(cce)    
            }    
                
            call YachtAvailability(yachtSpec, baseCode, baseDate, dateResult, yacht)    
        }

    
    
        -----------------------------------------------------------------------------    
    
        procedure SearchAllTypes()    
        {
call debug.DebugNL(("req.v : 2754 : p Request->BuildYachtList.SearchAllTypes [<>]",""))

    
            hashinst is schash.Hash with null    
            procedure AccomSearch(    
                baseDate is baseres.BaseDates,    
                dateResult is dateres.DateResult with null,    
                dateResList is dateres.DateResultList with null    
            )    
            {
call debug.DebugNL(("req.v : 2764 : p Request->BuildYachtList.SearchAllTypes.AccomSearch [<>][<>][<>]","_","_","_"))

    
                -----------------------------------------------------------------------------    
                procedure Process(    
                    baseDate is baseres.BaseDates,    
                    dateResult is dateres.DateResult with null,    
                    dateResList is dateres.DateResultList with null    
                )    
                {
call debug.DebugNL(("req.v : 2774 : p Request->BuildYachtList.SearchAllTypes.AccomSearch.Process [<>][<>][<>]","_","_","_"))

    
                    quick select as accTypeTu from acc_type    
                    where acc_type.F_type = catTypeTu->F_type    
                    order by F_loa_feet, F_avail_desc    
                    on ex.lock {
call debug.DebugNL(("req.v : 2781 : Request->BuildYachtList.SearchAllTypes.AccomSearch.Process.acc_type select <>",""))

    
                        --call myerror("One or more acc_type records skipped",2)    
                        accept    
                    }

    
                    {    
                        
                        let keyStr := gl_company_no^accomTu->F_accom_no^baseDate->baseCode^(string(dateResult->startDate) if dateResult != null, "" otherwise)    
                            
                        let uniqueEntry, ? := hashinst->UniqueEnter(keyStr)    
                        if uniqueEntry {    
                            if dateResList != null {    
                                let dateTmp := dateResList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart and dateRes->isValid {    
                                        call ProcessYacht(baseDate->baseCode, baseDate, dateRes)    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            } else {    
                                call ProcessYacht(baseDate->baseCode, baseDate, dateResult)    
                            }    
                        }    
                    }    
                }

    
                -----------------------------------------------------------------------------    
    
                if baseDate->yachtList = null {    
                    baseDate->yachtList := empty(accomres.YachtList)    
                }    
                gl_company_no := baseDate->companyNo    
                quick select unique avail.F_company_no, avail.F_base,    
                avail.F_accom_no, avail.F_display, avail.F_access    
                from avail index F_key_2    
                where avail.F_company_no = gl_company_no    
                and avail.F_base = baseDate->baseCode    
                and avail.F_display != "N"    
                and pub.AvailAccessOk(avail.F_access)    
                on ex.lock {
call debug.DebugNL(("req.v : 2826 : Request->BuildYachtList.SearchAllTypes.AccomSearch.avail select <>",""))

    
                    --call myerror("One or more avail records skipped",2)    
                    accept    
                }

    
                {    
                    quick select as accomTu from accom index F_accom_no    
                    where accom.F_accom_no = avail.F_accom_no    
                    and accom.F_type matches yachtType    
                    and fleet.CheckFleet(F_fleet)    
                    on ex.lock {
call debug.DebugNL(("req.v : 2840 : Request->BuildYachtList.SearchAllTypes.AccomSearch.accom select <>",""))

    
                        --call myerror("One or more accom records skipped",0)    
                        accept    
                    }

    
                    {    
                        if yachtCat = 0 {    
                            quick select as catTypeTu from cat_type index F_key    
                            where cat_type.F_product = yachtProduct    
                            and cat_type.F_company_no = gl_company_no    
                            and cat_type.F_type = accom.F_type    
                            order by F_category,F_sort_by    
                            on ex.lock {
call debug.DebugNL(("req.v : 2856 : Request->BuildYachtList.SearchAllTypes.AccomSearch.cat_type select <>",""))

    
                                --call myerror("One or more cat_type records skipped",2)    
                                accept    
                            }

    
                            {    
                                call Process(baseDate, dateResult, dateResList)    
                            }    
                        } else {    
                            quick select as catTypeTu from cat_type index F_key    
                            where cat_type.F_product = yachtProduct    
                            and cat_type.F_company_no = gl_company_no    
                            and cat_type.F_type = accom.F_type    
                            and cat_type.F_category = yachtCat    
                            order by F_category,F_sort_by    
                            on ex.lock {
call debug.DebugNL(("req.v : 2875 : Request->BuildYachtList.SearchAllTypes.AccomSearch.cat_type select <>",""))

    
                                --call myerror("One or more cat_type records skipped",2)    
                                accept    
                            }

    
                            {    
                                call Process(baseDate, dateResult, dateResList)    
                            }    
                        }    
                    }    
                }    
            }

    
    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -- body of SearchAllTypes    
    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
            if dateResultList = null or dateResultList->IsEmpty() {    
                let tmp := yachtBases->head with null    
                while (tmp != null) {    
                    let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                    call AccomSearch(baseDate, null)    
                    tmp := tmp->next    
                }    
                    
                    
            } else {    
                if holidayType = holtype.ClubYacht {    
                    -- TODO filter out end bases where start base is unavailable    
                    let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
                    while (tmp != null) {    
                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                        call AccomSearch(baseDate, null, dateResultList)    
                        tmp := tmp->next    
                    }    
                } else {    
                    let dateTmp := dateResultList->head with null    
                    while (dateTmp != null) {    
                        let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                        if dateRes->isStart and dateRes->isValid {    
                            let baseResultList := dateRes->baseResultList    
                            let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                            while baseTmp != null {    
                                let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                if baseResult->isValid {    
                                    let tmp := (yachtBases->head if yachtBases != null, null otherwise) with null    
                                    while (tmp != null) {    
                                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                        if baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                            call AccomSearch(baseDate, dateRes)    
                                        }    
                                        tmp := tmp->next    
                                    }    
                                }    
                                baseTmp := baseTmp->next    
                            }    
                        }    
                        dateTmp := dateTmp->next    
                    }    
                        
                }    
            }    
        }

     
    
        -----------------------------------------------------------------------------    
        procedure SearchThisType()    
        {
call debug.DebugNL(("req.v : 2952 : p Request->BuildYachtList.SearchThisType [<>]",""))

    
    
            hashinst is schash.Hash with null    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
    
            -----------------------------------------------------------------------------    
            procedure Process()    
            {
call debug.DebugNL(("req.v : 2963 : p Request->BuildYachtList.SearchThisType.Process [<>]",""))

    
                -----------------------------------------------------------------------------    
                procedure AvailSearch(    
                    baseDate is baseres.BaseDates,    
                    dateResult is dateres.DateResult with null,    
                    dateResList is dateres.DateResultList with null    
                )    
                {
call debug.DebugNL(("req.v : 2973 : p Request->BuildYachtList.SearchThisType.Process.AvailSearch [<>][<>][<>]","_","_","_"))

    
                    if baseDate->yachtList = null {    
                        baseDate->yachtList := empty(accomres.YachtList)    
                    }    
                    quick select unique avail.F_company_no, avail.F_base,    
                    avail.F_accom_no, avail.F_display,avail.F_access    
                    from avail index F_key    
                    where avail.F_company_no = gl_company_no    
                    and avail.F_base = baseDate->baseCode    
                    and avail.F_accom_no = accomTu->F_accom_no    
                    and avail.F_display != "N"    
                    and pub.AvailAccessOk(avail.F_access)    
                    on ex.lock {
call debug.DebugNL(("req.v : 2988 : Request->BuildYachtList.SearchThisType.Process.AvailSearch.avail select <>",""))

    
                        --call myerror("One or more avail records skipped",2)    
                        accept    
                    }

    
                    {    
                        let keyStr := gl_company_no^accomTu->F_accom_no^baseDate->baseCode^(string(dateResult->startDate) if dateResult != null, "" otherwise)    
                        let uniqueEntry, ? := hashinst->UniqueEnter(keyStr)    
                        if uniqueEntry {    
                            if dateResList != null {    
                                let dateTmp := dateResList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart {    
                                        call AvailSearch(baseDate, dateRes)    
                                        call ProcessYacht(baseDate->baseCode, baseDate, dateRes)    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            } else {    
                                call ProcessYacht(baseDate->baseCode, baseDate, dateResult)    
                            }    
                        }    
                    }    
                }

    
                -----------------------------------------------------------------------------    
                quick select as accTypeTu from acc_type    
                where acc_type.F_type = catTypeTu->F_type    
                order by F_loa_feet, F_avail_desc    
                on ex.lock {
call debug.DebugNL(("req.v : 3023 : Request->BuildYachtList.SearchThisType.Process.acc_type select <>",""))

    
                    --call myerror("One or more acc_type records skipped",2)    
                    accept    
                }

    
                {    
                    if MatchYachtRequests(null, accTypeTu) {    
                        quick select as accomTu from accom    
                        where accom.F_type = acc_type.F_type    
                        and fleet.CheckFleet(F_fleet)    
                        order by F_category,F_name    
                        on ex.lock {
call debug.DebugNL(("req.v : 3038 : Request->BuildYachtList.SearchThisType.Process.accom select <>",""))

    
                            --call myerror("One or more accom records skipped",2)    
                            accept    
                        }

    
                        {    
                            if dateResultList = null  or dateResultList->IsEmpty() {    
                                let tmpBase := yachtBases->head with null    
                                while (tmpBase != null) {    
                                    let baseDate := yachtBases->GetBaseDatesList(tmpBase) with null    
                                    if gl_company_no = baseDate->companyNo {    
                                        call AvailSearch(baseDate, null, null)    
                                    }    
                                    tmpBase := tmpBase->next    
                                }    
                            } else {    
                                if holidayType = holtype.ClubYacht {    
                                    -- TODO filter out end bases where start base is unavailable    
                                    let tmp := yachtBases->head with null    
                                    while (tmp != null) {    
                                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                        call AvailSearch(baseDate, null, dateResultList)    
                                        tmp := tmp->next    
                                    }    
                                } else {    
                                    let dateTmp := dateResultList->head with null    
                                    while (dateTmp != null) {    
                                        let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                        let baseResultList := dateRes->baseResultList    
                                        let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                                        if dateRes->isStart and dateRes->isValid {    
                                            while baseTmp != null {    
                                                let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                                if baseResult->isValid {    
                                                    let tmp := yachtBases->head with null    
                                                    while (tmp != null) {    
                                                        let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                                        if gl_company_no = baseDate->companyNo and    
        --    ###### TO DO doesn't work for second part of hol ##    
                                                           baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                                            call AvailSearch(baseDate, dateRes)    
                                                        }    
                                                        tmp := tmp->next    
                                                    }    
                                                }    
                                                baseTmp := baseTmp->next    
                                            }    
                                        }    
                                        dateTmp := dateTmp->next    
                                    }    
                                }    
                            }    
                        }    
                    }    
                }    
            }

    
    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -- body of SearchThisType    
    
            let compArr := Companies(yachtBases)    
            let compCnt := 1    
            while compArr[compCnt] != "" {    
                gl_company_no := compArr[compCnt]    
                if yachtCat = 0 {    
                    quick select as catTypeTu from cat_type index F_key    
                    where cat_type.F_product = yachtProduct    
                    and cat_type.F_company_no = gl_company_no    
                    and cat_type.F_type matches yachtType    
                    order by F_category,F_sort_by    
                    on ex.lock {
call debug.DebugNL(("req.v : 3116 : Request->BuildYachtList.SearchThisType.cat_type select <>",""))

    
                        --call myerror("One or more cat_type records skipped",2)    
                        accept    
                    }

    
                    {    
                        call Process()    
                    }    
                } else {    
                    quick select as catTypeTu from cat_type index F_key    
                    where cat_type.F_product = yachtProduct    
                    and cat_type.F_company_no = gl_company_no    
                    and cat_type.F_type matches yachtType    
                    and cat_type.F_category = yachtCat    
                    order by F_category,F_sort_by    
                    on ex.lock {
call debug.DebugNL(("req.v : 3135 : Request->BuildYachtList.SearchThisType.cat_type select <>",""))

    
                        --call myerror("One or more cat_type records skipped",2)    
                        accept    
                    }

    
                    {    
                        call Process()    
                    }    
                }    
                compCnt := compCnt + 1    
            }    
        }

    
    
        -----------------------------------------------------------------------------    
        --njh  
        procedure SearchThisAccom()    
        {
call debug.DebugNL(("req.v : 3157 : p Request->BuildYachtList.SearchThisAccom [<>]",""))

    
    
            hashinst is schash.Hash with null    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
    
            procedure ProcessSingleYacht()    
            {
call debug.DebugNL(("req.v : 3167 : p Request->BuildYachtList.SearchThisAccom.ProcessSingleYacht [<>]",""))

    
                procedure AvailSearch(    
                    baseDate is baseres.BaseDates,    
                    dateResult is dateres.DateResult with null,    
                    dateResList is dateres.DateResultList with null    
                )    
                {
call debug.DebugNL(("req.v : 3176 : p Request->BuildYachtList.SearchThisAccom.ProcessSingleYacht.AvailSearch [<>][<>][<>]","_","_","_"))

    
                    if baseDate->yachtList = null {    
                        baseDate->yachtList := empty(accomres.YachtList)    
                    }    
                    quick select unique avail.F_company_no, avail.F_base,    
                    avail.F_accom_no, avail.F_display,avail.F_access    
                    from avail index F_key    
                    where avail.F_company_no = gl_company_no    
                    and avail.F_base = baseDate->baseCode    
                    and avail.F_accom_no = accomTu->F_accom_no    
                    and avail.F_display != "N"    
                    and pub.AvailAccessOk(avail.F_access)    
                    on ex.lock {
call debug.DebugNL(("req.v : 3191 : Request->BuildYachtList.SearchThisAccom.ProcessSingleYacht.AvailSearch.avail select <>",""))

    
                        --call myerror("One or more avail records skipped",2)    
                        accept    
                    }

    
                    {    
                        let keyStr := gl_company_no^accomTu->F_accom_no^baseDate->baseCode^(string(dateResult->startDate) if dateResult != null, "" otherwise)    
                        let uniqueEntry, ? := hashinst->UniqueEnter(keyStr)    
                        if uniqueEntry {    
                            if dateResList != null {    
                                let dateTmp := dateResList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart {    
                                        call AvailSearch(baseDate, dateRes)    
                                        call ProcessYacht(baseDate->baseCode, baseDate, dateRes)    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            } else {    
                                call ProcessYacht(baseDate->baseCode, baseDate, dateResult)    
                            }    
                        }    
                    }    
                }

    
                -------------------------------------------------------------------------------------  
                -- body of ProcessSingleYacht  
  
                quick select as accTypeTu from acc_type    
                where acc_type.F_type = accomTu->F_type    
                on ex.lock {
call debug.DebugNL(("req.v : 3227 : Request->BuildYachtList.SearchThisAccom.ProcessSingleYacht.acc_type select <>",""))

  accept  }

    
                {   
  
                    quick select as catTypeTu from cat_type index F_key    
                    where cat_type.F_product = yachtProduct    
                    and cat_type.F_company_no = gl_company_no    
                    and cat_type.F_type = accomTu->F_type         
                    on ex.lock {
call debug.DebugNL(("req.v : 3239 : Request->BuildYachtList.SearchThisAccom.ProcessSingleYacht.cat_type select <>",""))

  accept  }

    
                    {}    
  
                    if (MatchYachtRequests(null, accTypeTu) and fleet.CheckFleet(accomTu->F_fleet))    
                    {    
                        if dateResultList = null  or dateResultList->IsEmpty() {    
                            let tmpBase := yachtBases->head with null    
                            while (tmpBase != null) {    
                                let baseDate := yachtBases->GetBaseDatesList(tmpBase) with null    
                                if gl_company_no = baseDate->companyNo {    
                                    call AvailSearch(baseDate, null, null)    
                                }    
                                tmpBase := tmpBase->next    
                            }    
                        } else {    
                            if holidayType = holtype.ClubYacht {    
                                -- TODO filter out end bases where start base is unavailable    
                                let tmp := yachtBases->head with null    
                                while (tmp != null) {    
                                    let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                    call AvailSearch(baseDate, null, dateResultList)    
                                    tmp := tmp->next    
                                }    
                            } else {    
                                let dateTmp := dateResultList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                    let baseResultList := dateRes->baseResultList    
                                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                                    if dateRes->isStart and dateRes->isValid {    
                                        while baseTmp != null {    
                                            let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                            if baseResult->isValid {    
                                                let tmp := yachtBases->head with null    
                                                while (tmp != null) {    
                                                    let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                                    if gl_company_no = baseDate->companyNo and    
    --    ###### TO DO doesn't work for second part of hol ##    
                                                    baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                                        call AvailSearch(baseDate, dateRes)    
                                                    }    
                                                    tmp := tmp->next    
                                                }    
                                            }    
                                            baseTmp := baseTmp->next    
                                        }    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            }    
                        }    
                    }    
                }    
            }

    
            ---------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -----------------------------------------------------------------------------    
            -- body of SearchThisAccom    
    
            let compArr := Companies(yachtBases)    
            let compCnt := 1    
            while compArr[compCnt] != "" {    
                gl_company_no := compArr[compCnt]    
                select as accomTu from accom    
                where F_accom_no = yachtAccomNo
                {
call debug.DebugNL(("req.v : 3311 : Request->BuildYachtList.SearchThisAccom.accom select <>",""))

    
                    call ProcessSingleYacht()    
                }

     
                compCnt := compCnt + 1    
            }    
        }

    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
        -- body of BuildYachtList    
    
        if (yachtAccomNo = 0)    
        { 
            if (yachtType = "*")    
            {    
                call    SearchAllTypes()    
            }    
            else    
            {    
                call    SearchThisType()    
            } 
        } 
        else    
        {    
            call    SearchThisAccom()    
        }    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
        -----------------------------------------------------------------------------    
    }

    
        ---------------------------------------------------------------------------------------------------------------------------------------------------------    
    function ResultMatchClubRequests(    
        room is accomres.RoomResult    
    ) returns boolean    
    {
call debug.DebugNL(("req.v : 3354 : f Request->ResultMatchClubRequests [<>]","_"))

    
        if accomRequests = null or accomRequests->clubRequest = null {    
call debug.DebugNL(("req.v : 3358 : ret Request->ResultMatchClubRequests <>[<>]","",true))
            return true    
        }

    
        let clubRequest := accomRequests->clubRequest    
        if clubRequest->adultOnly and !room->adultsOnly {    
call debug.DebugNL(("req.v : 3365 : ret Request->ResultMatchClubRequests <>[<>]","",false))
            return false    
        }

    
call debug.DebugNL(("req.v : 3370 : ret Request->ResultMatchClubRequests <>[<>]","",true))
        return true    
    }

    
    ------------------------------------------------------------------------------------------------------    
    function InvalidAccomForPax(    
        clientNo is large number,    
        accomPaxCat is string,    
        totalBedSpace is number,    
        adultKidPax is number    
    ) returns boolean    
    {
call debug.DebugNL(("req.v : 3383 : f Request->InvalidAccomForPax [<>][<>][<>][<>]",clientNo,accomPaxCat,totalBedSpace,adultKidPax))

    
        invalidAccomForPax is boolean := false    
        cotPax is number := 1    
        let endDate := startDate + travelDuration days    
        select pass.F_client_no, pass.F_pass_no    
        from pass index F_key    
        where pass.F_client_no = clientNo    
        {
call debug.DebugNL(("req.v : 3393 : Request->InvalidAccomForPax.pass select <>",""))

    
            let passngrAge, ? := passlink.GetPassengerAge(clientNo, pass.F_pass_no, endDate)    
            let paxType := passlink.GetAccomAgeCat(passngrAge)    
                
            case true {    
                value (paxType = passlink.GYBPax & accomPaxCat = "A")    
                    invalidAccomForPax := true    
                value (paxType = passlink.SUPax & accomPaxCat in ("A", "F"))    
                    invalidAccomForPax := true    
                value (paxType = passlink.SNAPPax & accomPaxCat in ("A", "F", "E"))    
                    invalidAccomForPax := true    
                value (paxType in (passlink.MINPax, passlink.COTPax))     
                    if (accomPaxCat in ("A", "F", "E", "D") or ((adultKidPax + cotPax) > totalBedSpace))    
                    {    
                        invalidAccomForPax := true    
                    } else {    
                        cotPax := cotPax + 1    
                    }    
            }    
        }

    
call debug.DebugNL(("req.v : 3417 : ret Request->InvalidAccomForPax <>[<>]","",invalidAccomForPax))
        return invalidAccomForPax    
    }

    
    ------------------------------------------------------------------------------------------------------    
    function MatchClubRequests(    
        accomTu is schema.accom    
    ) returns boolean    
    {
call debug.DebugNL(("req.v : 3427 : f Request->MatchClubRequests [<>]","_"))

    
        -- Adults only checks can only be made when we have the date.    
        if accomRequests = null or accomRequests->clubRequest = null {    
call debug.DebugNL(("req.v : 3432 : ret Request->MatchClubRequests <>[<>]","",true))
            return true    
        }

    
        let clubRequest := accomRequests->clubRequest    
        if clubRequest->singleClubAccom {    
            let totPax := adultPax + childPax    
            let maxPax := accomTu->F_max_sale    
            let totBeds := ((accomTu->F_dbl_beds * 2) + accomTu->F_sng_beds + accomTu->F_tot_xtra_beds)    
            if clubRequest->singles {    
                maxPax := accomTu->F_max_singles    
                if totPax > accomTu->F_max_singles {    
call debug.DebugNL(("req.v : 3445 : ret Request->MatchClubRequests <>[<>]","",false))
                    return false    
                }

    
            } else {     
                if accomTu->F_min_sale > totPax or totPax > accomTu->F_max_sale {    
call debug.DebugNL(("req.v : 3452 : ret Request->MatchClubRequests <>[<>]","",false))
                    return false    
                }

    
            }    
            if (partyClientNo != null) {    
                if InvalidAccomForPax(partyClientNo, accomTu->F_ok_child, totBeds, totPax) {    
call debug.DebugNL(("req.v : 3460 : ret Request->MatchClubRequests <>[<>]","",false))
                    return false    
                }

    
            } else {    
                if (accomTu->F_ok_child in ("A", "F") & childPax >= 1) {    
call debug.DebugNL(("req.v : 3467 : ret Request->MatchClubRequests <>[<>]","",false))
                    return false    
                }

    
            }    
        }    
        if clubRequest->balcony and accomTu->F_balcony != 'Y' {    
call debug.DebugNL(("req.v : 3475 : ret Request->MatchClubRequests <>[<>]","",false))
            return false    
        }

    
        if clubRequest->seaView and accomTu->F_sea_view != 'Y' {    
call debug.DebugNL(("req.v : 3481 : ret Request->MatchClubRequests <>[<>]","",false))
            return false    
        }

    
        if clubRequest->singles and accomTu->F_max_singles < 1 {    
call debug.DebugNL(("req.v : 3487 : ret Request->MatchClubRequests <>[<>]","",false))
            return false    
        }

    
        if clubRequest->cots and accomTu->F_cots = 0 {    
call debug.DebugNL(("req.v : 3493 : ret Request->MatchClubRequests <>[<>]","",false))
            return false    
        }

    
        if clubRequest->zbeds and accomTu->F_dbl_zbeds = 0 and    
           accomTu->F_sng_zbeds = 0 {    
call debug.DebugNL(("req.v : 3500 : ret Request->MatchClubRequests <>[<>]","",false))
            return false    
        }

    
call debug.DebugNL(("req.v : 3505 : ret Request->MatchClubRequests <>[<>]","",true))
        return true    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    procedure RoomAvailability(    
        roomSpec is accomres.RoomResult with null,    
        baseCode is string,    
        baseDate is baseres.BaseDates,    
        dateResult is dateres.DateResult with null,    
        room is accomres.RoomResult    
    )    
     {
call debug.DebugNL(("req.v : 3520 : p Request->RoomAvailability [<>][<>][<>][<>][<>]","_",baseCode,"_","_","_"))

    
         let singlesReqd := SinglesReqd(false)    
        let maxPax := (room->maxSingles if singlesReqd, room->maxPax otherwise)    
        let paxReqd := ((adultPax + childPax) if (SingleAccomReqd(false) & singlesReqd),     
                1 if singlesReqd, null otherwise)    
        if dateResult == null {    
            let dateRangeList := baseDate->dateRangeList    
            let tmpDate := dateRangeList->head with null    
            while (tmpDate != null) {    
                let dateRange := dateRangeList->GetDateRange(tmpDate)    
--                let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                let avbkDur := avbkdt.DaysToDuration(baseTravelDur)    
                avbkDate is avbkdt.DateTime with null    
                avbkDateRange is avbkdt.DateTimeRange with null    
                if leaway = 0 {    
                    avbkDate := avbkdt.DateToMidday(dateRange->startDate)    
                } else {    
                    avbkDateRange := empty(avbkdt.DateTimeRange)->Init(    
                                dateRange->startDate, dateRange->endDate)    
                }    
                let res := AVBKSearch(room->accomNo, avbkDate, avbkDur, baseDate->baseCode,     
                        baseDate->baseCode, avbkDateRange, baseDate->hasDelivery,     
                        maxPax, paxReqd) with null    
                        -- hourly    
                        -- ignoreAvail     
                call BuildResults(baseDate, room, null, res, baseres.ClubBase, avbkDate, avbkDur, singlesReqd, roomSpec, null)    
                tmpDate := tmpDate->next    
            }    
        } else {    
            let startDate := dateResult->startDate    
            if holidayType = holtype.YachtClub {    
                startDate := startDate + 7 days    
            }    
            let avbkDate := avbkdt.DateToMidday(startDate)    
            let avbkDur := dateResult->travelDuration    
            let res := AVBKSearch(room->accomNo, avbkDate, avbkDur, baseCode, baseCode, null,    
                    false, maxPax, paxReqd) with null    
                    -- hourly    
                    -- ignoreAvail     
            call BuildResults(baseDate, room, null, res, baseres.ClubBase, avbkDate, avbkDur, singlesReqd)    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    -- if roomSpec then only select rooms that match the criteria    
    public procedure BuildClubList(    
        roomSpec is accomres.RoomResult with null    
    )    
    {
call debug.DebugNL(("req.v : 3573 : p Request->BuildClubList [<>]","_"))

    
        let catAccTu := empty(schema.cat_acc)    
        let accomTu := empty(schema.accom)    
    
        if clubBases = null or clubBases->IsEmpty() {    
call debug.DebugNL(("req.v : 3580 : ret Request->BuildClubList <>",""))
            return    
        }    
    
        procedure ProcessRoom(    
            baseCode is string,    
            baseDate is baseres.BaseDates,    
            dateResult is dateres.DateResult with null    
        )    
        {
call debug.DebugNL(("req.v : 3590 : p Request->BuildClubList.ProcessRoom [<>][<>][<>]",baseCode,"_","_"))

    
            let room := accomres.BuildRoomResultFromAccom(accomTu, baseCode, adultPax, childPax, infantPax)    
            room->category := catAccTu->F_category    
            room->sortBy := catAccTu->F_sort_by    
            room->accomType := accomTu->F_type    
            if doInterconnecting in (InterconnectingOnly, NoInterconnecting, StdPlusInterconnecting) {    
                select * from accomrel    
                where F_accom_no = room->accomNo    
                and F_rel_level = "I"    
                {
call debug.DebugNL(("req.v : 3602 : Request->BuildClubList.ProcessRoom.accomrel select <>",""))

    
                    let tu := empty(schema.accom)    
                    quick select as tu from accom index F_accom_no    
                    where accom.F_accom_no = accomrel.F_rel_accom_no    
                    {
call debug.DebugNL(("req.v : 3609 : Request->BuildClubList.ProcessRoom.accomrel.accom select <>",""))

    
                        
                        let relRoom := accomres.BuildRoomResultFromAccom(tu, baseCode, adultPax, childPax, infantPax)    
                        relRoom->relatedRoomType := F_rel_level    
                        if room->relatedRoomList = null {    
                            room->relatedRoomList := empty(accomres.RoomList)    
                        }    
                        call room->relatedRoomList->Append(relRoom)    
                    }

    
                }

    
            }    
            if roomSpec != null and dateResult != null {    
                call room->SetAdultsOnly(dateResult->startDate, (dateResult->startDate + avbkdt.DurationToDays(dateResult->travelDuration) days))    
                if dateResult != null and !room->IsSameRoom(roomSpec) {    
                    -- If specification of room is not the same as required, then ignore it.    
call debug.DebugNL(("req.v : 3630 : ret Request->BuildClubList.ProcessRoom <>",""))
                    return    
                }    
            }    
            if (doInterconnecting = AllRooms or    
               (doInterconnecting = InterconnectingOnly and (room->relatedRoomList != null and !room->relatedRoomList->IsEmpty())) or    
               (doInterconnecting = NoInterconnecting and (room->relatedRoomList = null or room->relatedRoomList->IsEmpty())) or    
               doInterconnecting = StdPlusInterconnecting) {    
                call baseDate->roomList->Append(room)    
                if showHeldBookings {    
                    if baseDate->categoryList = null {    
                        baseDate->categoryList := empty(accomres.CategoryList)    
                    }    
                    let cce := empty(accomres.ClubCategoryElement)    
                    cce->category := room->category    
                    cce->sortBy := room->sortBy    
                    cce->accomType := room->accomType    
                    ? := baseDate->categoryList->ClubUniqueAppend(cce)    
                    if isInternet {    
                        call cce->setInetCat(baseCode,room->accomType,gl_company_no)    
                        call cce->setPriceList(baseCode,baseDate->endBaseCode,room->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc, adultPax, childPax)    
                    }    
                }    
                call RoomAvailability(roomSpec, baseCode, baseDate, dateResult, room)    
            }    
        }

    
        
        procedure    
        SearchByAvail(    
            baseCode is string,    
            baseDate is baseres.BaseDates with null,    
            dateResult is dateres.DateResult with null    
        )    
        {
call debug.DebugNL(("req.v : 3666 : p Request->BuildClubList.SearchByAvail [<>][<>][<>]",baseCode,"_","_"))

    
            hashinst is schash.Hash with null    
            hashinst := empty(schash.Hash)    
            call hashinst->SetHashSize(211)    
            quick select unique avail.F_company_no, avail.F_base,    
                avail.F_accom_no, avail.F_display,avail.F_access    
            from avail index F_key_2    
            where avail.F_company_no = gl_company_no    
            and avail.F_base = baseCode    
            and avail.F_display != "N"    
            and pub.AvailAccessOk(avail.F_access)    
            on ex.lock {
call debug.DebugNL(("req.v : 3680 : Request->BuildClubList.SearchByAvail.avail select <>",""))

    
                --call myerror("One or more avail records skipped",2)    
                accept    
            }

    
            {    
                quick select as accomTu from accom index F_accom_no    
                where accom.F_accom_no = avail.F_accom_no    
                and accom.F_type matches clubType    
                on ex.lock {
call debug.DebugNL(("req.v : 3693 : Request->BuildClubList.SearchByAvail.accom select <>",""))

    
                    --call myerror("One or more accom records skipped",0)    
                    accept    
                }

    
                {    
                    if MatchClubRequests(accomTu) {    
                        if clubCat = 0 {    
                            quick select as catAccTu from cat_acc    
                            where cat_acc.F_product = clubProduct    
                            and cat_acc.F_company_no = gl_company_no    
                            and cat_acc.F_accom_no = accomTu->F_accom_no    
                            order by cat_acc.F_category,cat_acc.F_sort_by    
                            on ex.lock {
call debug.DebugNL(("req.v : 3710 : Request->BuildClubList.SearchByAvail.cat_acc select <>",""))

    
                                --call myerror("One or more cat_acc records skipped",0)    
                                accept    
                            }

    
                            {    
                                let uniqueEntry, ? := hashinst->UniqueEnter(string(gl_company_no^accom.F_accom_no), null)    
                                if uniqueEntry {    
                                    call ProcessRoom(baseCode, baseDate, dateResult)    
                                }    
                            }    
                        } else {    
                            quick select as catAccTu from cat_acc    
                            where cat_acc.F_product = clubProduct    
                            and cat_acc.F_company_no = gl_company_no    
                            and cat_acc.F_accom_no = accomTu->F_accom_no    
                            and cat_acc.F_category = clubCat    
                            order by cat_acc.F_category,cat_acc.F_sort_by    
                            on ex.lock {
call debug.DebugNL(("req.v : 3732 : Request->BuildClubList.SearchByAvail.cat_acc select <>",""))

    
                                --call myerror("One or more cat_acc records skipped",0)    
                                accept    
                            }

    
                            {    
                                let uniqueEntry, ? := hashinst->UniqueEnter(string(gl_company_no^accom.F_accom_no), null)    
                                if uniqueEntry {    
                                    call ProcessRoom(baseCode, baseDate, dateResult)    
                                }    
                            }    
                        }    
                    }    
                }    
            }    
        }

    
    
        procedure    
        SearchByCat(    
        )    
        {
call debug.DebugNL(("req.v : 3758 : p Request->BuildClubList.SearchByCat [<>]",""))

    
            procedure AvailSearch(    
                accomNo is large number,    
                baseDate is baseres.BaseDates with null,    
                dateResult is dateres.DateResult with null    
            )    
            {
call debug.DebugNL(("req.v : 3767 : p Request->BuildClubList.SearchByCat.AvailSearch [<>][<>][<>]",accomNo,"_","_"))

    
                quick select from avail index F_key    
                where avail.F_company_no = baseDate->companyNo    
                and avail.F_accom_no = accomNo    
                and avail.F_base = baseDate->baseCode    
                and avail.F_display != "N"    
                and pub.AvailAccessOk(avail.F_access)    
                on ex.lock {
call debug.DebugNL(("req.v : 3777 : Request->BuildClubList.SearchByCat.AvailSearch.avail select <>",""))

    
                    --call myerror("One or more avail records skipped",2)    
                    accept    
                }

    
                {    
                    call ProcessRoom(baseDate->baseCode, baseDate, dateResult)    
                    stop    
                }    
            }

    
    
            procedure AccomSearch()    
            {
call debug.DebugNL(("req.v : 3795 : p Request->BuildClubList.SearchByCat.AccomSearch [<>]",""))

    
                quick select as accomTu from accom index F_accom_no    
                where accom.F_accom_no = catAccTu->F_accom_no    
                and accom.F_type matches clubType    
                on ex.lock {
call debug.DebugNL(("req.v : 3802 : Request->BuildClubList.SearchByCat.AccomSearch.accom select <>",""))

    
                    --call myerror("One or more accom records skipped",0)    
                    accept    
                }

    
                {    
                    if MatchClubRequests(accomTu) {    
                        if dateResultList == null {    
                            let tmp := clubBases->head with null    
                            while (tmp != null) {    
                                let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                if gl_company_no = baseDate->companyNo {    
                                    if baseDate->roomList = null {    
                                        baseDate->roomList := empty(accomres.RoomList)    
                                    }    
                                    call AvailSearch(accom.F_accom_no, baseDate, null)    
                                }    
                                tmp := tmp->next    
                            }    
                        } else {                                
                            if holidayType = holtype.YachtClub {    
                                -- TODO filter out end bases where start base is unavailable    
                                let tmp := clubBases->head with null    
                                while (tmp != null) {    
                                    let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                    if gl_company_no = baseDate->companyNo {    
                                        if baseDate->roomList = null {    
                                            baseDate->roomList := empty(accomres.RoomList)    
                                        }    
                                        let dateTmp := dateResultList->head with null    
                                        while (dateTmp != null) {    
                                            let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                            if dateRes->isStart {    
                                                call AvailSearch(accom.F_accom_no, baseDate, dateRes)    
                                            }    
                                            dateTmp := dateTmp->next    
                                        }    
                                    }    
                                    tmp := tmp->next    
                                }    
                            } else {    
                                let dateTmp := dateResultList->head with null    
                                while (dateTmp != null) {    
                                    let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                                    if dateRes->isStart and dateRes->isValid {    
                                        let baseResultList := dateRes->baseResultList    
                                        let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                                        while baseTmp != null {    
                                            let baseResult := baseResultList->GetBaseResult(baseTmp)                            
                                            if baseResult->isValid {    
                                                let tmp := clubBases->head with null    
                                                while (tmp != null) {    
                                                    let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                                    if gl_company_no = baseDate->companyNo and    
                                                       baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                                        if baseDate->roomList = null {    
                                                            baseDate->roomList := empty(accomres.RoomList)    
                                                        }    
                                                        call AvailSearch(accom.F_accom_no, baseDate, dateRes)    
                                                    }    
                                                    tmp := tmp->next    
                                                }    
                                            }    
                                            baseTmp := baseTmp->next    
                                        }    
                                    }    
                                    dateTmp := dateTmp->next    
                                }    
                            }    
                        }    
                    }    
                }    
    
    
                let compArr := Companies(clubBases)    
                let compCnt := 1    
                while compArr[compCnt] != "" {    
                    gl_company_no := compArr[compCnt]    
                    if clubCat = 0 {    
                        quick select as catAccTu from cat_acc index F_key    
                        where cat_acc.F_product = clubProduct    
                        and cat_acc.F_company_no = gl_company_no    
                        order by cat_acc.F_category,cat_acc.F_sort_by    
                        on ex.lock {
call debug.DebugNL(("req.v : 3889 : Request->BuildClubList.SearchByCat.AccomSearch.cat_acc select <>",""))

    
                            --call myerror("One or more cat_acc records skipped",0)    
                            accept    
                        }

    
                        {    
                            call AccomSearch()    
                        }    
                    } else {    
                        quick select as catAccTu from cat_acc index F_key    
                        where cat_acc.F_product = clubProduct    
                        and cat_acc.F_company_no = gl_company_no    
                        and cat_acc.F_category = clubCat    
                        order by cat_acc.F_category,cat_acc.F_sort_by    
                        on ex.lock {
call debug.DebugNL(("req.v : 3907 : Request->BuildClubList.SearchByCat.AccomSearch.cat_acc select <>",""))

    
                            --call myerror("One or more cat_acc records skipped",0)    
                            accept    
                        }

    
                        {    
                            call AccomSearch()    
                        }    
                    }    
                    compCnt := compCnt + 1    
                }    
            }

    
        }

    
    
        -- Go this route if there is only one base as well.    
        if clubBases->ElementCount() = 1 or    
           (clubCat = 0 and clubType = "*") {    
            if dateResultList = null or dateResultList->IsEmpty() {    
                let tmp := clubBases->head with null    
                while (tmp != null) {    
                    let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                    if baseDate->roomList = null {    
                        baseDate->roomList := empty(accomres.RoomList)    
                    }    
                    gl_company_no := baseDate->companyNo    
                    call SearchByAvail(baseDate->baseCode, baseDate, null)    
                    tmp := tmp->next    
                }    
            } else {    
                if holidayType = holtype.YachtClub {    
                    -- TODO filter out end bases where start base is unavailable    
                    let tmp := clubBases->head with null    
                    while (tmp != null) {    
                        let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                        if baseDate->roomList = null {    
                            baseDate->roomList := empty(accomres.RoomList)    
                        }    
                        gl_company_no := baseDate->companyNo    
                        let dateTmp := dateResultList->head with null    
                        while (dateTmp != null) {    
                            let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                            if dateRes->isStart {    
                                call SearchByAvail(baseDate->baseCode, baseDate, dateRes)    
                            }    
                            dateTmp := dateTmp->next    
                        }    
                        tmp := tmp->next    
                    }    
                } else {    
                    let dateTmp := dateResultList->head with null    
                    while (dateTmp != null) {    
                        let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                        if dateRes->isStart and dateRes->isValid {    
                            let baseResultList := dateRes->baseResultList    
                            let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                            while baseTmp != null {    
                                let baseResult := baseResultList->GetBaseResult(baseTmp)    
                                if baseResult->isValid {    
                                    let tmp := clubBases->head with null    
                                    while (tmp != null) {    
                                        let baseDate := clubBases->GetBaseDatesList(tmp) with null    
                                        if baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                            if baseDate->roomList = null {    
                                                baseDate->roomList := empty(accomres.RoomList)    
                                            }    
                                            gl_company_no := baseDate->companyNo    
                                            call SearchByAvail(baseDate->baseCode, baseDate, dateRes)    
                                        }    
                                        tmp := tmp->next    
                                    }    
                                }    
                                baseTmp := baseTmp->next    
                            }    
                        }    
                        dateTmp := dateTmp->next    
                    }    
                }    
            }    
        } else {    
            call SearchByCat()    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    BuildResults(    
        baseDate is baseres.BaseDates,    
        roomResult is accomres.RoomResult with null,    
        yachtResult is accomres.YachtResult with null,    
        avbkRes is avbk.AccomResult with null,    
        baseType is baseres.BaseType,    
        avbkDate is avbkdt.DateTime,    
        avbkDuration is avbkdt.Duration,    
        singlesReqd is boolean,    
        roomSpec is accomres.RoomResult with null,    
        yachtSpec is accomres.YachtResult with null    
    )    
    {
call debug.DebugNL(("req.v : 4014 : p Request->BuildResults [<>][<>][<>][<>][<>][<>][<>][<>][<>][<>]","_","_","_","_","_","_","_",singlesReqd,"_","_"))

    
    
  
        let tmpAccomDate := avbkRes->accomDateList->head with null    
        while tmpAccomDate != null {    
            let accomDate := cast(tmpAccomDate, avbk.AccomDateElement)    
            let dateResult := empty(dateres.DateResult) with null    
            dateResult->startDate := avbkdt.Date(accomDate->startDT)    
            dateResult->travelDuration := avbkDuration    
            tmpAccomDate := tmpAccomDate->next    
            if roomResult != null {    
                call roomResult->SetAdultsOnly(dateResult->startDate, (dateResult->startDate + avbkdt.DurationToDays(avbkDuration) days))    
                if !singlesReqd and roomResult->InvalidMinPax(adultPax + childPax) {    
call debug.DebugNL(("req.v : 4029 : ret Request->BuildResults <>",""))
                    return    
                }    
                if !roomResult->IsSameRoom(roomSpec) or    
                   !roomResult->IsSuitable(adultPax, childPax, infantPax) {    
                    -- If specification of room is not the same as required, then ignore it.    
call debug.DebugNL(("req.v : 4035 : ret Request->BuildResults <>",""))
                    return    
                }    
                if !ResultMatchClubRequests(roomResult)  {    
                    continue <<>>    
                }    
            }    
            if yachtResult != null {    
                call yachtResult->SetPremier(dateResult->startDate)    
                if !singlesReqd and yachtResult->InvalidMinPax(adultPax + childPax) {    
call debug.DebugNL(("req.v : 4045 : ret Request->BuildResults <>",""))
                    return    
                }    
                if !yachtResult->IsSameYacht(yachtSpec) {    
                    -- If specification of yacht is not the same as required, then ignore it.    
call debug.DebugNL(("req.v : 4050 : ret Request->BuildResults <>",""))
                    return    
                }    
                if !ResultMatchYachtRequests(yachtResult)  {    
                    continue <<>>    
                }    
            }    
            let actualDateResult := dateResultList->UniqueOrder(dateResult)    
            actualDateResult->isStart := actualDateResult->isStart or baseDate->isStartBase    
            --let baseResult := actualDateResult->UniqueAppendBase(baseDate->companyNo, baseDate->baseCode, baseDate->endBaseCode, baseType, baseDate->isStartBase, baseDate->isEndBase)    
            let baseResult := actualDateResult->UniqueAppendBase(baseDate->companyNo, accomDate->startBase, accomDate->endBase, baseType, baseDate->isStartBase, baseDate->isEndBase)    
            if baseResult->isValid {    
                if roomResult != null {    
                    let cce := empty(accomres.ClubCategoryElement)    
                    cce->category := roomResult->category    
                    cce->sortBy := roomResult->sortBy    
                    cce->accomType := roomResult->accomType    
                    if isInternet {    
                        call cce->setInetCat(baseResult->startBase,roomResult->accomType,gl_company_no)    
                        call cce->setPriceList(baseResult->startBase,baseResult->endBase,roomResult->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc,adultPax, childPax)    
                    }    
                    let actualCce := baseResult->accommodationList->clubResult->ClubUniqueOrder(cce)    
                    let room := roomResult->Clone()    
                    room->beforeGap := accomDate->bfrGapDur    
                    room->afterGap := accomDate->afrGapDur    
                    room->beforeBase := accomDate->bfrBase    
                    room->afterBase := accomDate->afrBase    
                    room->accomrefNo := accomDate->accomRef    
                    call room->CalculateStatus(baseResult->startBase, baseResult->endBase)    
                    if room->IsValidStatus(minClubStatus) {    
                        if roomResult->relatedRoomList != null {    
                            -- Search the interconnecting rooms to see if any are vacant on the specificed date.    
                            let relTmp := roomResult->relatedRoomList->head with null    
                            while relTmp != null {    
                                let relRoom := roomResult->relatedRoomList->GetRoomResult(relTmp)    
--display "Rel room", relRoom->accomNo, relRoom->name, avbkdt.Date(accomDate->startDT), avbkdt.DurationToDays(avbkDuration), baseResult->startBase    
                                call relRoom->SetAdultsOnly(dateResult->startDate, (dateResult->startDate + avbkdt.DurationToDays(avbkDuration) days))    
                                let singlesReqd := SinglesReqd(false)    
                                let maxPax := (relRoom->maxSingles if singlesReqd,     
                                            relRoom->maxPax otherwise)    
                                let paxReqd := ((adultPax + childPax) if (SingleAccomReqd(false) &     
                                            singlesReqd), 1 if singlesReqd, null otherwise)    
                                let res := AVBKSearch(relRoom->accomNo, accomDate->startDT, avbkDuration,     
                                        baseResult->startBase, baseResult->endBase, null,    
                                        baseDate->hasDelivery, maxPax, paxReqd) with null    
                                -- hourly    
                                -- ignoreAvail     
                                if res != null and res->accomDateList->elemCount != 0 {    
                                    let relAccomDate := cast(res->accomDateList->head, avbk.AccomDateElement)    
                                    let clonedRelRoom := relRoom->Clone()    
                                    clonedRelRoom->beforeGap := relAccomDate->bfrGapDur    
                                    clonedRelRoom->afterGap := relAccomDate->afrGapDur    
                                    clonedRelRoom->beforeBase := relAccomDate->bfrBase    
                                    clonedRelRoom->afterBase := relAccomDate->afrBase    
                                    call clonedRelRoom->CalculateStatus(baseResult->startBase, baseResult->endBase)    
                                    if clonedRelRoom->IsValidStatus(minClubStatus) {    
                                        if room->relatedRoomList = null {    
                                            room->relatedRoomList := empty(accomres.RoomList)    
                                        }    
                                        call room->relatedRoomList->Append(clonedRelRoom)    
                                    }     
                                }    
                                relTmp := relTmp->next    
                            }    
                        }     
                        if (doInterconnecting = AllRooms or    
                           (doInterconnecting = InterconnectingOnly and (room->relatedRoomList != null and !room->relatedRoomList->IsEmpty())) or    
                           (doInterconnecting = NoInterconnecting and (room->relatedRoomList = null or room->relatedRoomList->IsEmpty())) or    
                           doInterconnecting = StdPlusInterconnecting) {    
                               if (doInterconnecting = AllRooms and    
                               (room->relatedRoomList != null and !room->relatedRoomList->IsEmpty())) and    
                               coalesceAccom {    
                                -- Add the room in on its own, without the interconnecting status    
                                -- Only needed if the rooms are coalesced.    
                                let singleRoom := room->Clone()    
                                call actualCce->AddSameRoomResult(singleRoom)    
                            }    
                            if coalesceAccom {    
                                call room->CoalesceRooms()    
                                if singlesReqd or !room->InvalidMinPax(adultPax + childPax) {    
                                    call actualCce->AddSameRoomResult(room)    
                                }    
                            } else {    
                                call actualCce->AddRoomResult(room)    
                            }    
                            call ClubPromotions(baseResult, baseType, dateResult, cce, room)    
                        }    
                    }    
                }    
                if yachtResult != null {    
                                        findEnd is avbkdt.DateTime    
                                        findEnd := accomDate->startDT + dateResult->travelDuration     
                                        let dz, tz := avbkdt.DateAndTime(findEnd)    
                                        --display dz     
                            --display dateResult->startDate, dateResult->travelDuration    
                    let yce := empty(accomres.YachtCategoryElement)    
                    yce->category := yachtResult->category    
                    yce->sortBy := yachtResult->sortBy    
                    yce->accomType := yachtResult->accomType    
                    call yce->setPriceList(baseResult->startBase,baseResult->endBase,yachtResult->accomType,gl_company_no,dateResult->startDate,avbkdt.DurationToDays(dateResult->travelDuration),gl_origin,gl_lang,gl_loc, adultPax, childPax)    
                    let actualYce := baseResult->accommodationList->yachtResult->YachtUniqueOrder(yce)    
                    let yacht := yachtResult->Clone()    
                    yacht->beforeGap := accomDate->bfrGapDur    
                    yacht->afterGap := accomDate->afrGapDur    
                    yacht->beforeBase := accomDate->bfrBase    
                    yacht->afterBase := accomDate->afrBase    
                    yacht->accomrefNo := accomDate->accomRef    
                                        if gl_company_no = "5" and dz > 26/10/2009 and dz < 02/11/2009 {    
                                                yacht->afterGap := 0    
                                                }    
                                        let uz, wz := avbkdt.DateAndTime(accomDate->startDT)    
                                        if gl_company_no = "5" and uz > 15/03/2009 and uz < 11/04/2009 {    
                                                yacht->beforeGap := 0    
                                                }    
    
                    call yacht->CalculateStatus(baseResult->startBase, baseResult->endBase)    
                    if yacht->IsValidStatus(minYachtStatus) {    
                          
 
                        if coalesceAccom {    
                            call actualYce->AddSameYachtResult(yacht)    
                        } else {    
                            call actualYce->AddYachtResult(yacht)    
                        }    
                        call YachtPromotions(baseResult, baseType, dateResult, yce, yacht)    
                    }    
                }    
                if baseDate->isStartBase {    
                    -- Count the number of accommodation options for the start date.    
                    resultCount := resultCount + 1    
                }    
            }    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    ClubPromotions(    
        origBaseResult is baseres.BaseResult,    
        baseType is baseres.BaseType,    
        dateResult is dateres.DateResult,    
        cce is accomres.ClubCategoryElement,    
        roomResult is accomres.RoomResult    
    )    
    {
call debug.DebugNL(("req.v : 4197 : p Request->ClubPromotions [<>][<>][<>][<>][<>]","_","_","_","_","_"))

    
        if !doPromotions {    
call debug.DebugNL(("req.v : 4201 : ret Request->ClubPromotions <>",""))
            return    
        }    
        if roomResult->status = accomres.BlueStatus {    
            let actualDateResult := promotionResultList->dateResultList->UniqueOrder(dateResult->Clone())    
            let baseResult := actualDateResult->UniqueAppendBase(origBaseResult->companyNo, origBaseResult->startBase, origBaseResult->endBase, baseType, origBaseResult->isStartBase, origBaseResult->isEndBase, false)    
            let actualCce := baseResult->accommodationList->clubResult->ClubUniqueOrder(cce->Clone())    
            let room := roomResult->Clone()    
            call actualCce->AddRoomResult(room)    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    YachtPromotions(    
        origBaseResult is baseres.BaseResult,    
        baseType is baseres.BaseType,    
        dateResult is dateres.DateResult,    
        yce is accomres.YachtCategoryElement,    
        yachtResult is accomres.YachtResult with null    
    )    
    {
call debug.DebugNL(("req.v : 4225 : p Request->YachtPromotions [<>][<>][<>][<>][<>]","_","_","_","_","_"))

    
        if !doPromotions {    
call debug.DebugNL(("req.v : 4229 : ret Request->YachtPromotions <>",""))
            return    
        }    
        if yachtResult->status = accomres.BlueStatus {    
            let actualDateResult := promotionResultList->dateResultList->UniqueOrder(dateResult->Clone())    
            let baseResult := actualDateResult->UniqueAppendBase(origBaseResult->companyNo, origBaseResult->startBase, origBaseResult->endBase, baseType, origBaseResult->isStartBase, origBaseResult->isEndBase, false)    
            let actualYce := baseResult->accommodationList->yachtResult->YachtUniqueOrder(yce->Clone())    
            let yacht := yachtResult->Clone()    
            call yacht->SetPremier(dateResult->startDate)    
            call actualYce->AddYachtResult(yacht)    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public function Display(indent is number)    
    returns text    
    {
call debug.DebugNL(("req.v : 4248 : f Request->Display [<>]",indent))

    
        let indStr := disp.Indent(indent)    
        txt is text    
        txt := txt ^ indStr ^ "Request: " ^ description ^ ""    
        indent := indent+1    
        indStr := disp.Indent(indent)    
        txt := txt ^ indStr ^ "company: " ^ company ^ ""    
        txt := txt ^ indStr ^ "startDate: " ^ startDate ^ ""    
        txt := txt ^ indStr ^ "travelTime: " ^ travelTime ^ ""    
        txt := txt ^ indStr ^ "travelDuration: " ^ travelDuration ^ ""    
        txt := txt ^ indStr ^ "leaway: " ^ leaway ^ ""    
        txt := txt ^ indStr ^ "holidayType: " ^ holidayType ^ ""    
        txt := txt ^ indStr ^ "product: " ^ product ^ ""    
        txt := txt ^ indStr ^ "\tclubProduct: " ^ clubProduct ^ ""    
        txt := txt ^ indStr ^ "\tyachtProduct: " ^ yachtProduct ^ ""    
        txt := txt ^ indStr ^ "area: " ^ area ^ ""    
        txt := txt ^ indStr ^ "clubStartBase: " ^ clubStartBase ^ ""    
        txt := txt ^ indStr ^ "yachtStartBase: " ^ yachtStartBase ^ ""    
        txt := txt ^ indStr ^ "yachtEndBase: " ^ yachtEndBase ^ ""    
        txt := txt ^ indStr ^ "adultPax: " ^ adultPax ^ ""    
        txt := txt ^ indStr ^ "childPax: " ^ childPax ^ ""    
        txt := txt ^ indStr ^ "clubCat: " ^ clubCat ^ ""    
        txt := txt ^ indStr ^ "clubType: " ^ clubType ^ ""    
        txt := txt ^ indStr ^ "yachtCat: " ^ yachtCat ^ ""    
        txt := txt ^ indStr ^ "yachtType: " ^ yachtType ^ ""    
        txt := txt ^ indStr ^ "price: " ^ price ^ ""    
        txt := txt ^ indStr ^ "doInterconnecting: " ^ doInterconnecting ^ ""    
        txt := txt ^ indStr ^ "showHeldBookings:" ^ showHeldBookings ^ ""    
        txt := txt ^ indStr ^ "showAvailableBases:" ^ showAvailableBases ^ ""    
        txt := txt ^ indStr ^ "clubBases:"    
        if clubBases != null {    
            txt := txt ^ clubBases->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo club bases"    
        }    
        txt := txt ^ indStr ^ "yachtBases:"    
        if yachtBases != null {    
            txt := txt ^ yachtBases->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo yacht bases"    
        }    
        txt := txt ^ indStr ^ "Flight Requests:"    
        if flightRequests != null {    
            txt := txt ^ flightRequests->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo flight requests"    
        }    
        txt := txt ^ indStr ^ "Accommodation Requests:"    
        if accomRequests != null {    
            txt := txt ^ accomRequests->Display(indent+1)    
        } else {    
            txt := txt ^ indStr ^ "\tNo accommodation requests"    
        }    
call debug.DebugNL(("req.v : 4303 : ret Request->Display <>[<>]","",txt))
        return txt    
    }

    
        
    ------------------------------------------------------------------------------------------------------    
    procedure Flights(    
        baseList is baseres.BaseDatesList with null,    
        baseType is baseres.BaseType    
    )    
    {
call debug.DebugNL(("req.v : 4315 : p Request->Flights [<>][<>]","_","_"))

    
        -- Hash list to ensure that routelink searches are only performed once per airport.    
        if !((gl_company_no = "1" or gl_company_no = "7") and gl_inv_co = "1") {    
            -- flights are not applicable    
call debug.DebugNL(("req.v : 4321 : ret Request->Flights <>",""))
            return    
        }    
        let hashinst := empty(schash.Hash)    
        call hashinst->SetHashSize(211)    
    
        function MatchesFlightRequest(    
            route is string    
        ) returns boolean    
        {
call debug.DebugNL(("req.v : 4331 : f Request->Flights.MatchesFlightRequest [<>]",route))

    
            if flightRequests = null or flightRequests->airportList = null or    
               flightRequests->airportList->IsEmpty() {    
call debug.DebugNL(("req.v : 4336 : ret Request->Flights.MatchesFlightRequest <>[<>]","",true))
                return true    
            }

    
            let tmp := flightRequests->airportList->head with null    
            while tmp != null {    
                let airport := flightRequests->airportList->GetAirport(tmp)    
                if route matches airport->airportCode ^ "*" {    
call debug.DebugNL(("req.v : 4345 : ret Request->Flights.MatchesFlightRequest <>[<>]","",true))
                    return true    
                }

    
                tmp := tmp->next    
            }    
call debug.DebugNL(("req.v : 4352 : ret Request->Flights.MatchesFlightRequest <>[<>]","",false))
            return false    
        }

    
    
        procedure OutBound(    
            baseDate is baseres.BaseDates,    
            baseType is baseres.BaseType,    
            searchStartDate is date,    
            searchEndDate is date,    
            arrAirport is string,    
            avbkDur is avbkdt.Duration    
        )    
        {
call debug.DebugNL(("req.v : 4367 : p Request->Flights.OutBound [<>][<>][<>][<>][<>][<>]","_","_",searchStartDate,searchEndDate,arrAirport,"_"))

    
            let uniqueEntry, ? := hashinst->UniqueEnter(string(arrAirport^searchStartDate^searchEndDate))    
            if uniqueEntry {    
                dat is date with null    
                actualDateResult is dateres.DateResult with null    
                let rTu := empty(schema.routlink)    
                select as rTu from routlink index F_date    
                where F_route matches "*" ^ arrAirport    
                and searchStartDate <= F_date <= searchEndDate    
                order by F_date,F_time asc    
                {
call debug.DebugNL(("req.v : 4380 : Request->Flights.OutBound.routlink select <>",""))

    
                        
                    on ex.pattern {    
                        accept    
                    }    
                    found is boolean := false    
                    depAirport is string    
                    arrAirport is string    
                    depAirport ^ "-" ^ arrAirport := rTu->F_route    
                    select * from airorigin    
                    where F_code = depAirport    
                    and F_origin = gl_origin    
                    {
call debug.DebugNL(("req.v : 4395 : Request->Flights.OutBound.routlink.airorigin select <>",""))

    
                        found := true    
                    }

    
                    if found and MatchesFlightRequest(rTu->F_route) {    
                        let stdRoute := empty(flightres.RouteResult)    
                        let starRoute := empty(flightres.RouteResult)    
                        call stdRoute->InitFromRoute(rTu, false, true)    
                        call starRoute->InitFromRoute(rTu, true, true)    
                        select * from routflight    
                        where F_route_no = rTu->F_route_no    
                        {
call debug.DebugNL(("req.v : 4410 : Request->Flights.OutBound.routlink.routflight select <>",""))

    
                            if dat != rTu->F_date {    
                                let dateResult := empty(dateres.DateResult) with null    
                                dateResult->startDate := routlink.F_date    
                                dateResult->travelDuration := avbkDur    
                                actualDateResult := dateResultList->UniqueOrder(dateResult)    
                                actualDateResult->isStart := actualDateResult->isStart or baseDate->isStartBase    
                                let baseResult := actualDateResult->UniqueAppendBase(baseDate->companyNo, baseDate->baseCode, baseDate->endBaseCode, baseType, baseDate->isStartBase, baseDate->isEndBase)    
                                dat := rTu->F_date    
                            }    
                            call flightrout.FindFlight(routflight.F_flight_no, flightProduct, travelDuration, arrAirport, adultPax, childPax, doPartial, isInternet, stdRoute, starRoute)    
                        }

    
                        if stdRoute->flightList != null and stdRoute->flightList->elemCount != 0 and    
                           !stdRoute->starClass and (flightRequests = null or !flightRequests->premiumSeats) {    
                            stdRoute := actualDateResult->routeList->UniqueAppend(stdRoute)    
                        }    
--display "starRoute", starRoute->Display(1)    
                        if starRoute->flightList != null and starRoute->flightList->elemCount != 0 and    
                           starRoute->starClass {    
                            starRoute := actualDateResult->routeList->UniqueAppend(starRoute)    
                        }    
                    }    
                }

    
            }    
        }

    
    
        procedure InBound()    
        {
call debug.DebugNL(("req.v : 4446 : p Request->Flights.InBound [<>]",""))

    
            procedure InRoute(    
                outRoute is flightres.RouteResult    
            )    
            {
call debug.DebugNL(("req.v : 4453 : p Request->Flights.InBound.InRoute [<>]","_"))

    
                let rTu := empty(schema.routlink)    
                let depDate := outRoute->arrDate + travelDuration days    
                let route := empty(flightres.RouteResult)    
--display "Search", outRoute->arrAirport ^ '-' ^ outRoute->depAirport, outRoute->depNo, depDate, outRoute->starClass    
                select as rTu from routlink index F_date    
                where F_route = outRoute->arrAirport ^ '-' ^ outRoute->depAirport    
                and F_dep_no = outRoute->depNo    
                and depDate <= F_date <= (depDate + 1 day)    
                order by F_route, F_date,F_time asc    
                {
call debug.DebugNL(("req.v : 4466 : Request->Flights.InBound.InRoute.routlink select <>",""))

    
                    select * from routflight    
                    where F_route_no = rTu->F_route_no    
                    order by F_date,F_time asc    
                    {
call debug.DebugNL(("req.v : 4473 : Request->Flights.InBound.InRoute.routlink.routflight select <>",""))

    
                        call route->InitFromRoute(rTu, outRoute->starClass, false)    
                        if outRoute->starClass {    
                            call flightrout.FindFlight(routflight.F_flight_no, flightProduct, travelDuration, outRoute->depAirport, adultPax, childPax, doPartial, isInternet, null, route)    
                        } else {    
                            call flightrout.FindFlight(routflight.F_flight_no, flightProduct, travelDuration, outRoute->depAirport, adultPax, childPax, doPartial, isInternet, route, null)    
                        }    
                    }

    
                    stop    
                }

    
                outRoute->inBoundRoute := route    
            }

    
        
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                let tmpRoute := dateRes->routeList->head with null    
                while tmpRoute != null {    
                    let outRoute := dateRes->routeList->GetRouteResult(tmpRoute)    
--display outRoute->Display(0)    
                    call InRoute(outRoute)    
                    tmpRoute := tmpRoute->next    
                    if (flightRequests = null or !doPartial) and    
                        !outRoute->IsCompleteRoute() {    
                        ? := dateRes->routeList->ElemDelete(outRoute)    
                    }    
                
                }    
                dateTmp := dateTmp->next    
            }    
        }

    
    
        if baseList != null and (dateResultList = null or dateResultList->IsEmpty()) {    
            let outBoundCount := 0    
            let tmpBase := baseList->head with null    
            while tmpBase != null {    
                let baseDate := baseList->GetBaseDatesList(tmpBase) with null    
                let outBaseTu := cache.GetBase(baseDate->companyNo, baseDate->baseCode)    
                let inBaseTu := cache.GetBase(baseDate->companyNo, baseDate->endBaseCode)    
                let dateRangeList := baseDate->dateRangeList    
                let tmpDate := dateRangeList->head with null    
                while (tmpDate != null) {    
                    let dateRange := dateRangeList->GetDateRange(tmpDate)    
                    let avbkDur := avbkdt.DaysToDuration(baseTravelDur)    
--                    let avbkDur := avbkdt.DaysToDuration((dateRange->endDate - dateRange->startDate) as days)     
                    if baseDate->isStartBase {    
                        call OutBound(baseDate, baseType,     
                            dateRange->startDate, dateRange->endDate,     
                            outBaseTu->F_airport, avbkDur)    
                    }    
                    tmpDate := tmpDate->next    
                }    
                tmpBase := tmpBase->next    
            }    
        } else if dateResultList != null and baseList != null {    
            let outBoundCount := 0    
            let dateTmp := dateResultList->head with null    
            while (dateTmp != null) {    
                let dateRes := dateResultList->GetDateResult(dateTmp) with null    
                if dateRes->isStart {    
                    let baseResultList := dateRes->baseResultList    
                    let baseTmp := (baseResultList->head if baseResultList != null, null otherwise) with null    
                    while baseTmp != null {    
                        let baseResult := baseResultList->GetBaseResult(baseTmp)    
                        if baseResult->isValid {    
                            let outBaseTu := cache.GetBase(baseResult->companyNo, baseResult->startBase)    
                            let inBaseTu := cache.GetBase(baseResult->companyNo, baseResult->endBase)    
                            let tmp := baseList->head with null    
                            while (tmp != null) {    
                                let baseDate := yachtBases->GetBaseDatesList(tmp) with null    
                                if baseres.BaseResultEqualBaseDate(baseResult, baseDate) {    
                                    --outBoundCount := outBoundCount + OutBound(baseDate, outBaseTu, inBaseTu, dateRes->startDate, dateRes->travelDuration, baseType, 0)    
                                    call OutBound(baseDate, baseType, dateRes->startDate, dateRes->startDate, outBaseTu->F_airport, dateRes->travelDuration)    
                                }    
                                tmp := tmp->next    
                            }    
                        }    
                        baseTmp := baseTmp->next    
                    }    
                }    
                dateTmp := dateTmp->next    
            }    
        }    
        call InBound()    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    public procedure    
    RelatedRooms(    
        room is accomres.RoomResult    
    )    
    {
call debug.DebugNL(("req.v : 4577 : p Request->RelatedRooms [<>]","_"))

    
        if !room->hasRelated {    
            room->hasRelated := true    
            select * from accomrel    
            where F_accom_no = room->accomNo    
            order by F_rel_level    
            {
call debug.DebugNL(("req.v : 4586 : Request->RelatedRooms.accomrel select <>",""))

    
                if (doInterconnecting in (AllRooms, NoInterconnecting) or    
                   (doInterconnecting in (InterconnectingOnly, StdPlusInterconnecting) and F_rel_level != 'I')) {    
                    let tu := empty(schema.accom)    
                    quick select as tu from accom index F_accom_no    
                    where accom.F_accom_no = accomrel.F_rel_accom_no    
                    {
call debug.DebugNL(("req.v : 4595 : Request->RelatedRooms.accomrel.accom select <>",""))

    
                        let relRoom := accomres.BuildRoomResultFromAccom(tu, room->baseCode, adultPax, childPax, infantPax)    
                        relRoom->relatedRoomType := F_rel_level    
                        relRoom->baseCode := room->baseCode    
                        if room->relatedRoomList = null {    
                            room->relatedRoomList := empty(accomres.RoomList)    
                        }    
                        call room->relatedRoomList->Append(relRoom)    
                    }

    
                }    
            }

    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    proc AddHeldOptions(    
        travelDate is date,    
        travelDur is avbkdt.Duration,    
        baseRes is baseres.BaseResult,    
        clubCategoryElem is accomres.ClubCategoryElement with null,    
        yachtCategoryElem is accomres.YachtCategoryElement with null,    
        room is accomres.RoomResult with null,    
        yacht is accomres.YachtResult with null    
    )    
    {
call debug.DebugNL(("req.v : 4628 : p Request->AddHeldOptions [<>][<>][<>][<>][<>][<>][<>]",travelDate,"_","_","_","_","_","_"))

    
        accomNo is large number    
        if room != null {    
            accomNo := room->accomNo    
        } else {    
            accomNo := yacht->accomNo    
        }    
        singlesReqd is boolean := SinglesReqd(!(baseRes->baseType = baseres.ClubBase))    
        singleAccomReqd is boolean := SingleAccomReqd(!(baseRes->baseType = baseres.ClubBase))    
        maxSingles is small number with null    
        if singlesReqd {    
            let accomTpl := empty(schema.accom)    
            select one as accomTpl from accom    
                where accom.F_accom_no = accomNo {
call debug.DebugNL(("req.v : 4644 : Request->AddHeldOptions.accom select <>",""))

    
            }

    
            ?, maxSingles := pub.GetMaxPax(gl_company_no, accomTpl, null)    
        }    
        let rqt := empty(avbk.Request)    
        call rqt->Init(    
            accomNo,    
            avbkdt.DateToMidday(travelDate),    
            travelDur,    
            null,    
            baseRes->startBase,    
            baseRes->endBase,    
            false,    
            null,    
            (null if !singlesReqd, (adultPax + childPax) if singleAccomReqd, 1 otherwise),    
            null,    
            maxSingles,    
            false,    
            true)    
    
        let bkgResultList := empty(avbk.Controller)->FindBookings(rqt)    
        if !bkgResultList->IsEmpty() {    
            let bkgPtr := cast(bkgResultList->head, avbk.BookResult) with null    
            while bkgPtr != null {    
                heldBooking is boolean := false    
                if bkgPtr->singlesPax = null {    
                    if book.book_status(bkgPtr->clientNo) = "H" {    
                        if clubCategoryElem != null {    
                            let heldResult := empty(accomres.HeldRoomResult)    
                            call heldResult->InitFromRoom(room)    
                            heldResult->accomNo := accomNo    
                            heldResult->baseCode := baseRes->startBase    
                            heldResult->clientNo := bkgPtr->clientNo    
                            heldResult->accomrefNo := bkgPtr->accomRef    
                            heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                            heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                            heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                            heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                            heldResult->singlesPax := bkgPtr->singlesPax    
                            heldResult->maxSingles := bkgPtr->maxSingles    
                            if room->relatedRoomList != null {    
                                -- Search the interconnecting rooms to see if any are held    
                                if heldResult->relatedRoomList = null {    
                                    heldResult->relatedRoomList := empty(accomres.RoomList)    
                                }    
                                let relTmp := room->relatedRoomList->head with null    
                                while relTmp != null {    
                                    let relRoom := room->relatedRoomList->GetRoomResult(relTmp)    
                                    let rqt := empty(avbk.Request)    
                                    call rqt->Init(    
                                        relRoom->accomNo,    
                                        avbkdt.DateToMidday(travelDate),    
                                        travelDur,    
                                        null,    
                                        baseRes->startBase,    
                                        baseRes->endBase,    
                                        false,    
                                        null,    
                                        (null if !singlesReqd, (adultPax + childPax) if singleAccomReqd, 1 otherwise),    
                                        null,    
                                        maxSingles,    
                                        false,    
                                        true)    
        
                                    let relBkgResultList := empty(avbk.Controller)->FindBookings(rqt)    
                                    if !relBkgResultList->IsEmpty() {    
                                        let relBkgPtr := cast(relBkgResultList->head, avbk.BookResult) with null    
                                        let endDate := avbkdt.Date(relBkgPtr->endDT)    
                                        if book.book_status(relBkgPtr->clientNo) = "H" {    
                                            let relHeldResult := empty(accomres.HeldRoomResult)    
                                            call relHeldResult->InitFromRoom(relRoom)    
                                            relHeldResult->accomNo := relRoom->accomNo    
                                            relHeldResult->baseCode := baseRes->startBase    
                                            relHeldResult->clientNo := relBkgPtr->clientNo    
                                            relHeldResult->accomrefNo := relBkgPtr->accomRef    
                                            relHeldResult->startDate := avbkdt.Date(relBkgPtr->startDT)    
                                            relHeldResult->startTime := avbkdt.TimeOfDay(relBkgPtr->startDT)    
                                            relHeldResult->endDate := avbkdt.Date(relBkgPtr->endDT)    
                                            relHeldResult->endTime := avbkdt.TimeOfDay(relBkgPtr->endDT)    
                                            relHeldResult->singlesPax := relBkgPtr->singlesPax    
                                            relHeldResult->maxSingles := relBkgPtr->maxSingles    
                                            call heldResult->relatedRoomList->Append(relHeldResult)    
                                        }    
                                    } else {    
                                        let clonedRelRoom := relRoom->Clone()    
                                        call heldResult->relatedRoomList->Append(clonedRelRoom)    
                                    }    
                                    relTmp := relTmp->next    
                                }    
    
                            }     
                                
                            let cce := clubCategoryElem->Clone()    
                            let actualCce := baseRes->accommodationList->clubResult->ClubUniqueOrder(cce)    
                            call actualCce->AddHeldRoomResult(heldResult)    
                            actualCce->heldOptCategory := true    
                        } else {    
                            let heldResult := empty(accomres.HeldYachtResult)    
                            heldResult->accomNo := accomNo    
                            heldResult->baseCode := baseRes->startBase    
                            heldResult->clientNo := bkgPtr->clientNo    
                            heldResult->accomrefNo := bkgPtr->accomRef    
                            heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                            heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                            heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                            heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                            heldResult->singlesPax := bkgPtr->singlesPax    
                            heldResult->maxSingles := bkgPtr->maxSingles    
                            call heldResult->InitFromYacht(yacht)    
                                
                            if yachtCategoryElem != null {    
                                let cce := yachtCategoryElem->Clone()    
                                let actualCce := baseRes->accommodationList->yachtResult->YachtUniqueOrder(cce)    
                                call actualCce->AddHeldYachtResult(heldResult)    
                                actualCce->heldOptCategory := true    
                            }    
                        }    
                    }    
                } else {    
                    let sglPtr := cast(bkgPtr->singlesBookResultList->head, avbk.BookResult) with null    
                    while sglPtr != null {    
    
                        if book.book_status(sglPtr->clientNo) = "H" {    
                            if clubCategoryElem != null {    
                                let heldResult := empty(accomres.HeldRoomResult)    
                                heldResult->accomNo := accomNo    
                                heldResult->baseCode := baseRes->startBase    
                                heldResult->clientNo := sglPtr->clientNo    
                                heldResult->accomrefNo := sglPtr->accomRef    
                                heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                                heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                                heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                                heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                                heldResult->singlesPax := sglPtr->singlesPax    
                                heldResult->maxSingles := bkgPtr->maxSingles    
                                call heldResult->InitFromRoom(room)    
    
                                let cce := clubCategoryElem->Clone()    
                                let actualCce := baseRes->accommodationList->clubResult->ClubUniqueOrder(cce)    
                                call actualCce->AddHeldRoomResult(heldResult)    
                                actualCce->heldOptCategory := true    
                            } else {    
                                if yachtCategoryElem != null {    
                                    let heldResult := empty(accomres.HeldYachtResult)    
                                    heldResult->accomNo := accomNo    
                                    heldResult->baseCode := baseRes->startBase    
                                    heldResult->clientNo := sglPtr->clientNo    
                                    heldResult->accomrefNo := sglPtr->accomRef    
                                    heldResult->startDate := avbkdt.Date(bkgPtr->startDT)    
                                    heldResult->startTime := avbkdt.TimeOfDay(bkgPtr->startDT)    
                                    heldResult->endDate := avbkdt.Date(bkgPtr->endDT)    
                                    heldResult->endTime := avbkdt.TimeOfDay(bkgPtr->endDT)    
                                    heldResult->singlesPax := sglPtr->singlesPax    
                                    heldResult->maxSingles := bkgPtr->maxSingles    
                                    call heldResult->InitFromYacht(yacht)    
    
                                    let cce := yachtCategoryElem->Clone()    
                                    let actualCce := baseRes->accommodationList->yachtResult->YachtUniqueOrder(cce)    
                                    call actualCce->AddHeldYachtResult(heldResult)    
                                    actualCce->heldOptCategory := true    
                                }    
                            }    
                        }    
                        sglPtr := cast(sglPtr->next, avbk.BookResult)    
                    }    
                }    
                bkgPtr := cast(bkgPtr->next, avbk.BookResult)    
            }    
        }    
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    procedure CategoryAccommodation(    
        travelDate is date,    
        travelDur is avbkdt.Duration,    
        baseRes is baseres.BaseResult,    
        baseDates is baseres.BaseDates,    
        catElem is accomres.CategoryElement    
    )    
    {
call debug.DebugNL(("req.v : 4830 : p Request->CategoryAccommodation [<>][<>][<>][<>][<>]",travelDate,"_","_","_","_"))

    
        procedure ClubCategoryAccomodation(    
            roomList is accomres.RoomList with null,    
            clubCatElem is accomres.ClubCategoryElement    
        )    
        {
call debug.DebugNL(("req.v : 4838 : p Request->CategoryAccommodation.ClubCategoryAccomodation [<>][<>]","_","_"))

    
            let tmp := (roomList->head if roomList != null, null otherwise) with null    
            while tmp != null {    
                let room := roomList->GetRoomResult(tmp)    
                tmp := tmp->next    
                if room->category = clubCatElem->category and    
                   room->accomType = clubCatElem->accomType {    
                    call AddHeldOptions(travelDate, travelDur, baseRes,     
                        clubCatElem, null, room, null)    
                }    
            }    
        }

        
    
        procedure YachtCategoryAccomodation(    
            yachtList is accomres.YachtList with null,    
            yachtCatElem is accomres.YachtCategoryElement    
        )    
        {
call debug.DebugNL(("req.v : 4860 : p Request->CategoryAccommodation.YachtCategoryAccomodation [<>][<>]","_","_"))

    
            let tmp := (yachtList->head if yachtList != null, null otherwise) with null    
            while tmp != null {    
                let yacht := yachtList->GetYachtResult(tmp)    
                tmp := tmp->next    
                if yacht->category = yachtCatElem->category and    
                   yacht->accomType = yachtCatElem->accomType {    
                    call AddHeldOptions(travelDate, travelDur, baseRes,     
                        null, yachtCatElem, null, yacht)    
                }    
            }    
        }

        
    
        if baseDates->roomList != null and !baseDates->roomList->IsEmpty() {    
            on ex.null {    
                display "CategoryAccommodation - club", catElem->scriptName, catElem->className    
            }    
            let clubCatElem := cast(catElem, accomres.ClubCategoryElement)    
            call ClubCategoryAccomodation(baseDates->roomList, clubCatElem)    
        } else if baseDates->yachtList != null and !baseDates->yachtList->IsEmpty() {    
            on ex.null {    
                display "CategoryAccommodation - yacht", catElem->scriptName, catElem->className    
            }    
            let yachtCatElem := cast(catElem, accomres.YachtCategoryElement)    
            call YachtCategoryAccomodation(baseDates->yachtList, yachtCatElem)    
        }    
                
    }

    
    
    ------------------------------------------------------------------------------------------------------    
    procedure AddHeldBookings()    
    {
call debug.DebugNL(("req.v : 4898 : p Request->AddHeldBookings [<>]",""))

    
        proc ProcessCategories(    
            processClubs is boolean,    
            dateRes is dateres.DateResult,    
            baseRes is baseres.BaseResult,    
            baseDates is baseres.BaseDates,    
            catElem is accomres.CategoryElement    
        )    
        {
call debug.DebugNL(("req.v : 4909 : p Request->AddHeldBookings.ProcessCategories [<>][<>][<>][<>][<>]",processClubs,"_","_","_","_"))

    
            if processClubs {    
                if baseRes->accommodationList->clubResult = null or     
                    baseRes->accommodationList->clubResult->IsEmpty() or     
                    !baseRes->accommodationList->clubResult->CategoryMatchNotEmpty(catElem)    
                {    
                    call CategoryAccommodation(dateRes->startDate, dateRes->travelDuration,    
                        baseRes, baseDates, catElem)    
                }    
            } else {    
                if baseRes->accommodationList->yachtResult = null or     
                    baseRes->accommodationList->yachtResult->IsEmpty() or     
                    !baseRes->accommodationList->yachtResult->CategoryMatchNotEmpty(catElem)    
                {    
                    call CategoryAccommodation(dateRes->startDate, dateRes->travelDuration,    
                        baseRes, baseDates, catElem)    
                }    
            }    
        }

    
        proc ProcessBaseDates(    
            dateRes is dateres.DateResult,    
            baseRes is baseres.BaseResult    
        )    
        {
call debug.DebugNL(("req.v : 4937 : p Request->AddHeldBookings.ProcessBaseDates [<>][<>]","_","_"))

    
            if baseRes->baseType = baseres.ClubBase {    
                let baseDates := clubBases->GetBaseResultMatch(baseRes) with null    
                if baseDates != null and baseDates->categoryList != null and     
                    !baseDates->categoryList->IsEmpty()    
                {    
                    let tmpCat := baseDates->categoryList->head with null    
                    while tmpCat != null {    
                        let catElem := baseDates->categoryList->GetCategoryElement(tmpCat)    
                        tmpCat := tmpCat->next    
                        call ProcessCategories(true, dateRes, baseRes, baseDates, catElem)    
                    }    
                }    
            } else {    
                let baseDates := yachtBases->GetBaseResultMatch(baseRes) with null    
                if baseDates != null and baseDates->categoryList != null and     
                    !baseDates->categoryList->IsEmpty()    
                {    
                    let tmpCat := baseDates->categoryList->head with null    
                    while tmpCat != null {    
                        let catElem := baseDates->categoryList->GetCategoryElement(tmpCat)    
                        tmpCat := tmpCat->next    
                        call ProcessCategories(false, dateRes, baseRes, baseDates, catElem)    
                    }    
                }    
            }    
        }

    
        proc ProcessBases(dateRes is dateres.DateResult)    
        {
call debug.DebugNL(("req.v : 4970 : p Request->AddHeldBookings.ProcessBases [<>]","_"))

    
            let baseResList := dateRes->baseResultList with null    
            if baseResList != null and !baseResList->IsEmpty() {    
                let tmpBaseRes := baseResList->head with null    
                while tmpBaseRes != null {    
                    let baseRes := baseResList->GetBaseResult(tmpBaseRes)    
                    tmpBaseRes := tmpBaseRes->next    
                    call ProcessBaseDates(dateRes, baseRes)    
                }    
            }    
        }

    
        if dateResultList != null and !dateResultList->IsEmpty() {    
            let tmpDateRes := dateResultList->head with null    
            while tmpDateRes != null {    
                let dateRes := dateResultList->GetDateResult(tmpDateRes)    
                tmpDateRes := tmpDateRes->next    
                call ProcessBases(dateRes)    
            }    
        }    
    }

        
}

    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
--------end of Request class def ---------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
------------------------------------------------------------------------------------------------------    
        
public function BuildRequest(    
    startDate is date,    
    travelDuration is number,    
    leaway is number,    
    holidayTypeCode is number,    
    product is string,    
    area is string,    
    clubStartBase is string with null,    
    yachtStartBase is string with null,    
    yachtEndBase is string with null,    
    adultPax is number,    
    childPax is number,    
    clubCat is number,    
    clubType is string,    
    yachtCat is number,    
    yachtType is string,    
    sourceVal is string,    
    partyClientNum is large number with null    
) returns Request with null    
{
call debug.DebugNL(("req.v : 5027 : f BuildRequest [<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>][<>]",startDate,travelDuration,leaway,holidayTypeCode,product,area,"_","_","_",adultPax,childPax,clubCat,clubType,yachtCat,yachtType,sourceVal,"_"))

    
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
call debug.DebugNL(("req.v : 5055 : ret BuildRequest <>[<>]","","_"))
    return req    
}

    
        
function Companies(    
    baseList is baseres.BaseDatesList with null    
)    
returns array of string    
{
call debug.DebugNL(("req.v : 5066 : f Companies [<>]","_"))

    
    companyArr is array[numberOfCompanies] of string    
    for i = 1 to numberOfCompanies {    
        companyArr[i] := ""    
    }    
    let compCnt := 0    
    if baseList != null {    
        let tmpBase := baseList->head with null    
        while tmpBase != null {    
            let baseDate := baseList->GetBaseDatesList(tmpBase) with null    
            let found := false    
            for j = 1 to compCnt {    
                if baseDate->companyNo = companyArr[j] {    
                    found := true    
                    break <<>>    
                }    
            }    
            if !found {    
                compCnt := compCnt + 1    
                companyArr[compCnt] := baseDate->companyNo    
            }    
            tmpBase := tmpBase->next    
        }    
    }    
call debug.DebugNL(("req.v : 5092 : ret Companies <>[<>]","","_"))
    return companyArr    
}
'''
    
    

