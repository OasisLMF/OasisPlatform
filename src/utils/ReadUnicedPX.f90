C File ReadUnicedPX.f

	!module ReadUnicedePX
	!contains
!
!******************************************************************************
!
      integer function GetUpxRecordType(upx_str,polid60)
!
!     Copyright (C) 2008-2009. Applied Research Associates, Inc. All rights reserved.
!
!     This code may not be duplicated or redistributed without the written
!     permission of Applied Research Associated, Inc.
!
!
!     Purpose: Returns the record type of a Unicede/px record if the record type 
!     is 61-65; returns file version times 10 (e.g., v9.5 --> 95) if record type 
!     is ***1 (header); otherwise, the return value is zero.
!
!******************************************************************************
!
      implicit none
      character*(*) upx_str
      character*20 rt_str
      character*100 temp_str
      integer ilen
      integer i
      integer istart
      integer iend
	integer istartver
	integer kount
	real version
      integer StringToInteger
	real StringToReal
      character*(*) polid60       ! policy ID (up to 32 characters) -- only returned for record type = 60
      integer istart2
      integer iend2
	integer i2

      GetUpxRecordType=0
      polid60='                                '

      rt_str='                    '
      ilen=LEN_TRIM(upx_str)

      do i=1,ilen
        if (upx_str(i:i) .ne. ' ') goto 100
      end do
      return
 100  continue
      istart=i

      do i=istart,ilen
        if (upx_str(i:i) .eq. ',') goto 200
      end do
      return
 200  continue
      iend=i-1

      rt_str(1:iend-istart+1)=upx_str(istart:iend)

      if (rt_str(1:4) .eq. '***1') then         ! header record, return version number (9 or 10)
	  istartver=0
	  kount=0
	  do i=5,ilen
	    if (StringToInteger(upx_str(i:i)) .eq. -99999) then
            if (istartver .eq. 0) then
              goto 300
	      else 
	        if (upx_str(i:i) .eq. ',') then
	          temp_str(1:kount)=upx_str(istartver:istartver+kount-1)
                version=StringToReal(temp_str(1:kount))				! format: ##.# or ##.##
                if (version .lt. -99998.9) then
							version=StringToReal(temp_str(1:kount-2))		! format: ##.#.#
							if (version .lt. -99998.9) then
								version=StringToReal(temp_str(1:kount-3))	! format: ##.#.##
							end if
						end if
						GetUpxRecordType=nint(10.*version)
	          if (GetUpxRecordType .ne. 90 .and. 
     &              GetUpxRecordType .ne. 95 .and.
     &              GetUpxRecordType .ne. 100 .and.
     &              GetUpxRecordType .ne. 105 .and.
     &              GetUpxRecordType .ne. 110 .and.
     &              GetUpxRecordType .ne. 115 .and.
     &              GetUpxRecordType .ne. 120 .and.
     &              GetUpxRecordType .ne. 125 .and.
     &              GetUpxRecordType .ne. 130 .and.
     &              GetUpxRecordType .ne. 140) then
                  GetUpxRecordType=0
	          end if
	          return
	        end if
	      end if
          else if (istartver .eq. 0) then
            istartver=i
          end if
	    kount=kount+1
 300      continue
        end do    
      else if (iend-istart+1 .eq. 2) then
        if (rt_str(1:2) .eq. '60') then         ! policy record (60) -- Required; must be first line of upx file
			GetUpxRecordType=60
			istart2=iend+2
			do i2=istart2,ilen
				if (upx_str(i2:i2) .ne. ' ') goto 400
			end do
			return
 400			continue
			istart2=i2
			do i2=istart2,ilen
				if (upx_str(i2:i2) .eq. ',') then
					iend2=i2-1
					goto 500
				end if
			end do
			return
 500			continue
          polid60=upx_str(istart2:iend2)        ! 02 policy ID (up to 32 characters)
        else if (rt_str(1:2) .eq. '61') then    ! layer record (61) -- Optional
          GetUpxRecordType=61
        else if (rt_str(1:2) .eq. '62') then    ! sublimit record (62) -- Optional; must immediately follow 61
          GetUpxRecordType=62
        else if (rt_str(1:2) .eq. '63') then    ! location record (63) -- Required
          GetUpxRecordType=63
        else if (rt_str(1:2) .eq. '64') then    ! location detail record (64) -- Optional (US, CA only); must immediately follow 63
          GetUpxRecordType=64
        else if (rt_str(1:2) .eq. '65') then    ! workers' comp record (65) -- Optional (U.S. only); must follow 63 and 64 (if applicable)
          GetUpxRecordType=65
        end if
      end if

      return
      end
!
!******************************************************************************
!
      integer function ParsePolicyRecord(upx_str,iversion,polid,
     &        Name,Address,UDF1,UDF2,UDF3,UDF4,UDF5,
     &        InsuredIDType,InsuredID,EffFrom,EffTo,
     &        Currency,ExchRate,UserLOB,Peril,
     &        PolForm,Status,ContractType)
!
!     returns field values of a Unicede/px policy record;
!     if the record type is 60 (policy record), the return value is 60;
!     otherwise, the return value is zero.
!
!     Versions 9.x - 14.x -- 20 fields
!
!******************************************************************************
!
      implicit none

      character*(*) upx_str       ! upx location record string
	integer iversion            ! upx file verion x 10 (must be 90, 95, 100, 105, 110, 115, 120, 125, 130 or 140)

      character*(*) polid         ! 02 policy ID (up to 32 characters)
      character*(*) Name          ! 03 name of insured party (up to 60 characters)
      character*(*) Address       ! 04 insured's address, not used in analysis (up to 100 characters)
      character*(*) UDF1          ! 05 user defined field 1 (up to 20 characters)
      character*(*) UDF2          ! 06 user defined field 2 (up to 20 characters)
      character*(*) UDF3          ! 07 user defined field 3 (up to 20 characters)
      character*(*) UDF4          ! 08 user defined field 4 (up to 20 characters)
      character*(*) UDF5          ! 09 user defined field 5 (up to 20 characters)
      character*(*) InsuredIDType ! 10 type of insured ID code (up to 6 characters): AMB, FEIN, USER, X
      character*(*) InsuredID     ! 11 insured ID code (up to 20 characters)
      integer EffFrom             ! 12 effective start date (YYYYMMDD)
      integer EffTo               ! 13 last day policy is effective (YYYYMMDD)
      character*(*) Currency      ! 14 currency name (up to 3 characters): USD
      integer ExchRate            ! 15 currency exchange rate -- future use -- enter 0
      character*(*) UserLOB       ! 16 user's line of business (up to 10 characters)
      character*(*) Peril         ! 17 policy peril code (up to 30 characters)
      character*(*) PolForm       ! 18 user defined policy form (up to 10 characters)
      character*(*) Status        ! 19 policy status (1 character): S=Submitted, Q=Quoted, B=Bound, C=Cancelled, R=Rejected
      character*(*) ContractType  ! 20 contract type (up to 3 characters): PP=Primary Property, PWC=Primary Workers' Compensation (skipped)
!
! local variables
!
      character*20 rt_str
      character*100 temp_str
      integer ilen
      integer k
      integer i
      integer istart
      integer iend
      integer klen
	integer ivermajor
      integer StringToInteger
      real StringToReal
!
! initializations
!
      ParsePolicyRecord=0
      polid=    '                                '    ! 02 policy ID (up to 32 characters)
      Name=     '                              '//    ! 03 name of insured party (up to 60 characters)
     &          '                              '
      Address=  '                              '//    ! 04 insured's address, not used in analysis (up to 100 characters)
     &          '                              '//
     &          '                                        '
      UDF1=     '                      '              ! 05 user defined field 1 (up to 20 characters)
      UDF2=     '                      '              ! 06 user defined field 2 (up to 20 characters)
      UDF3=     '                      '              ! 07 user defined field 3 (up to 20 characters)
      UDF4=     '                      '              ! 08 user defined field 4 (up to 20 characters)
      UDF5=     '                      '              ! 09 user defined field 5 (up to 20 characters)
      InsuredIDType='      '                          ! 10 type of insured ID code (up to 6 characters): AMB, FEIN, USER, X
      InsuredID='                      '              ! 11 insured ID code (up to 20 characters)
      EffFrom=0                   ! 12 effective start date (YYYYMMDD)
      EffTo=0                     ! 13 last day policy is effective (YYYYMMDD)
      Currency='   '              ! 14 currency name (up to 3 characters): USD
      ExchRate=0                  ! 15 currency exchange rate -- future use -- enter 0
      UserLOB='          '        ! 16 user's line of business (up to 10 characters)
      Peril=    '                              '      ! 17 policy peril code (up to 30 characters)
      PolForm='          '        ! 18 user defined policy form (up to 10 characters)
      Status=' '                  ! 19 policy status (1 character): S=Submitted, Q=Quoted, B=Bound, C=Cancelled, R=Rejected
      ContractType='   '          ! 20 contract type (up to 3 characters): PP=Primary Property, PWC=Primary Workers' Compensation (skipped)

	ivermajor=iversion/10
      rt_str='                    '
      ilen=LEN_TRIM(upx_str)

      istart=1
      do k=1,20
        do i=istart,ilen
          if (upx_str(i:i) .ne. ' ') goto 100
        end do
        return
 100    continue
        istart=i

        do i=istart,ilen
          if (upx_str(i:i) .eq. ',') then
            iend=i-1
            goto 200
	    else if (k .eq. 20 .and. i .eq. ilen) then
            iend=ilen
            goto 200
	    end if
        end do
        return
 200    continue
        temp_str=upx_str(istart:iend)

        if (k .eq. 1) then
          if (temp_str(1:2) .eq. '60') then
            ParsePolicyRecord=60                ! 01 record type code (up to 4 characters)
          else
            ParsePolicyRecord=0
          end if

        else if (k .eq. 2) then
          polid=upx_str(istart:iend)            ! 02 policy ID (up to 32 characters)

        else if (k .eq. 3) then
          Name=upx_str(istart:iend)             ! 03 name of insured party (up to 60 characters)

        else if (k .eq. 4) then
          Address=upx_str(istart:iend)          ! 04 insured's address, not used in analysis (up to 100 characters)

        else if (k .eq. 5) then
          UDF1=upx_str(istart:iend)             ! 05 user defined field 1 (up to 20 characters)

        else if (k .eq. 6) then
          UDF2=upx_str(istart:iend)             ! 06 user defined field 2 (up to 20 characters)

        else if (k .eq. 7) then
          UDF3=upx_str(istart:iend)             ! 07 user defined field 3 (up to 20 characters)

        else if (k .eq. 8) then
          UDF4=upx_str(istart:iend)             ! 08 user defined field 4 (up to 20 characters)

        else if (k .eq. 9) then
          UDF5=upx_str(istart:iend)             ! 09 user defined field 5 (up to 20 characters)

        else if (k .eq. 10) then
          InsuredIDType=upx_str(istart:iend)    ! 10 type of insured ID code (up to 6 characters): AMB, FEIN, USER, X
          if (InsuredIDType .ne. 'AMB' .and.
     &        InsuredIDType .ne. 'FEIN' .and.
     &        InsuredIDType .ne. 'USER' .and.
     &        InsuredIDType .ne. 'X') then
            ParsePolicyRecord=-k
          end if

        else if (k .eq. 11) then
          InsuredID=upx_str(istart:iend)        ! 11 insured ID code (up to 20 characters)

        else if (k .eq. 12) then
          EffFrom=StringToInteger(temp_str)     ! 12 effective start date (YYYYMMDD)
          if (EffFrom .lt. 0) then
            ParsePolicyRecord=-k
          end if

        else if (k .eq. 13) then
          EffTo=StringToInteger(temp_str)				! 13 last day policy is effective (YYYYMMDD)
          if (EffTo .lt. 0) then
            ParsePolicyRecord=-k
          end if

        else if (k .eq. 14) then
          Currency=upx_str(istart:iend)					! 14 currency name (up to 3 characters): USD
          if (Currency .ne. 'USD') then
            ParsePolicyRecord=-k
          end if

        else if (k .eq. 15) then
          ExchRate=StringToInteger(temp_str)		! 15 currency exchange rate -- future use -- enter 0
          if (ExchRate .ne. 0) then
            ParsePolicyRecord=-k
          end if

        else if (k .eq. 16) then
          UserLOB=upx_str(istart:iend)					! 16 user's line of business (up to 10 characters)

        else if (k .eq. 17) then
          Peril=upx_str(istart:iend)						! 17 policy peril code (up to 30 characters)

        else if (k .eq. 18) then
          PolForm=upx_str(istart:iend)					! 18 user defined policy form (up to 10 characters)

        else if (k .eq. 19) then
          Status=upx_str(istart:iend)						! 19 policy status (1 character): S=Submitted, Q=Quoted, B=Bound, C=Cancelled, R=Rejected

        else if (k .eq. 20) then
          ContractType=upx_str(istart:iend)			! 20 contract type (up to 3 characters): PP=Primary Property, PWC=Primary Workers' Compensation (skipped)

        end if
        istart=iend+2
      end do

      return
      end
!
!******************************************************************************
!
      integer function ParseLayerRecord(upx_str,iversion,polid,
     &        layerid,Premium,Peril,LimitType,Limit1,Limit2,
     &        AttachPt,LimitA,LimitB,LimitC,LimitD,
     &        AttachPtA,AttachPtB,AttachPtC,AttachPtD,
     &        DedType,DedAmt1,DedAmt2,Reinst,
     &        ReinsCount,ReinsOrder,ReinsType,ReinsCID,
     &        ReinsField1,ReinsField2,ReinsField3,ReinsField4)
!
!     returns field values of a Unicede/px sublimit record;
!     if the record type is 61 (layer record), the return value is 61;
!     otherwise, the return value is zero.
!
!     Versions 9.x -- 21 fields
!     Versions 10.x, 11.x, 12.x, 13.x, 14.x -- 29 fields (inserts fields 10-17)
!
!     First 9 fields are the same in all versions
!
!******************************************************************************
!
      implicit none

	integer, parameter :: maxre=5 ! maximum number of ceded reinsurance contracts that protect any one layer

      character*(*) upx_str       ! upx location record string
	integer iversion            ! upx file verion x 10 (must be 90, 95, 100, 105, 110, 115, 120, 125, 130 or 140)

      character*(*) polid         ! 02 policy ID (up to 32 characters)
      character*(*) layerid       ! 03 layer ID (up to 60 characters)
	real Premium                ! 04 total premium received for this layer
      character*(*) Peril         ! 05 layer peril code (up to 30 characters)
      character*(*) LimitType     ! 06 layer limit type (up to 6 characters): B=blanket, E=excess, *** not supported *** C=limit by coverage, CB=combined limit for A+B+C with separate for D, CSL100=offshore, CSLAI=offshore
      real Limit1                 ! 07 layer limit field 1 for layer types B (total insured or "blanket" limit) or E (primary limit), CSL100 or CSLAI (layer limit) -- not use for layer types C or CB
      real Limit2                 ! 08 layer limit field 2 for layer types E or C (gross limit)
      real AttachPt               ! 09 attachment point fo this layer

      real LimitA                 ! XX/10 layer limit field for layer types C, CB, CSL100, or CSLAI (enter 0 for types B and E)
      real LimitB                 ! XX/11 layer limit field for layer types C, CSL100, or CSLAI (enter 0 for other types)
      real LimitC                 ! XX/12 layer limit field for layer types C, CSL100, or CSLAI (enter 0 for other types)
      real LimitD                 ! XX/13 layer limit field for layer types C, CB, CSL100, or CSLAI (enter 0 for types B and E)
      real AttachPtA              ! XX/14 attachment point for layer types C, CB (enter 0 for other types)
      real AttachPtB              ! XX/15 attachment point for layer type C (enter 0 for other types)
      real AttachPtC              ! XX/16 attachment point for layer type C (enter 0 for other types)
      real AttachPtD              ! XX/17 attachment point for layer types C, CB (enter 0 for other types)

      character*(*) DedType       ! 10/18 deductible type: NO, AP, BL, FR, MA, MA2, MM, MM2, MI, MI2, PL (up to 3 characters)
      real DedAmt1                ! 11/19 deductible amount 1: minimum for types MM, MM2, MI, MI2; maximum for MA, MA2; blanket deduc for BL, FR, percentage for PL
      real DedAmt2                ! 12/20 deductible amount 2: maximum for types MM, MM2
      integer Reinst              ! 13/21 maximum number of reinstatements (reserved for future use, enter 0)

      integer ReinsCount          ! 14/22 number of ceded reinsurance contracts that protect this layer (if none enter 0 and stop parsing record; otherwise, repeat fields 23-29 for each contract)
      integer ReinsOrder(maxre)     ! 15/23 reinsurance order
      character*4 ReinsType(maxre)  ! 16/24 ceded reinsurance type (up to 4 characters): PFCP=proportional facultative as ceded %, PFCA=proportional facultative as ceded amount, NFG=non-proportional facultative in terms of insurers gross limit; SS=surplus share treaty
      character*32 ReinsCID(maxre)  ! 17/25 reinsurance certificate or program ID (up to 32 characters)
      real ReinsField1(maxre)       ! 18/26 ceded reinsurance field 1 for types PFCP (fraction ceded), PFCA (amount ceded), NFG or SS (layer number of ceded excess)
      real ReinsField2(maxre)       ! 19/27 ceded reinsurance field 2 for types NFG or SS (gross limit of the layer)
      real ReinsField3(maxre)       ! 20/28 ceded reinsurance field 3 for types NFG or SS (attachment point of the layer) 
      real ReinsField4(maxre)       ! 21/29 ceded reinsurance field 4 for types NFG or SS (fraction of the layer ceded)
!
! local variables
!
      character*20 rt_str
      character*100 temp_str
      integer ilen
      integer k
      integer i
      integer istart
      integer iend
      integer klen
	integer ivermajor
      integer StringToInteger
      real StringToReal
	integer kren
	integer krem
!
! initializations
!
      ParseLayerRecord=0
      polid=    '                                '    ! 02 policy ID (up to 32 characters)
      layerid=  '                              '//
     &          '                              '      ! 03 layer ID (up to 60 characters)
	Premium=0.0                                     ! 04 total premium received for this layer
      Peril=    '                              '      ! 05 layer peril code (up to 30 characters)
      LimitType='    '            ! 06 layer limit type (up to 6 characters): B=blanket, E=excess, *** not supported *** C=limit by coverage, CB=combined limit for A+B+C with separate for D, CSL100=offshore, CSLAI=offshore
      Limit1=0.0                  ! 07 layer limit field 1 for layer types B (total insured or "blanket" limit) or E (primary limit), CSL100 or CSLAI (layer limit) -- not use for layer types C or CB
      Limit2=0.0                  ! 08 layer limit field 2 for layer types E or C (gross limit)
      AttachPt=0.0                ! 09 attachment point fo this layer

      LimitA=0.0                  ! XX/10 layer limit field for layer types C, CB, CSL100, or CSLAI (enter 0 for types B and E)
      LimitB=0.0                  ! XX/11 layer limit field for layer types C, CSL100, or CSLAI (enter 0 for other types)
      LimitC=0.0                  ! XX/12 layer limit field for layer types C, CSL100, or CSLAI (enter 0 for other types)
      LimitD=0.0                  ! XX/13 layer limit field for layer types C, CB, CSL100, or CSLAI (enter 0 for types B and E)
      AttachPtA=0.0               ! XX/14 attachment point for layer types C, CB (enter 0 for other types)
      AttachPtB=0.0               ! XX/15 attachment point for layer type C (enter 0 for other types)
      AttachPtC=0.0               ! XX/16 attachment point for layer type C (enter 0 for other types)
      AttachPtD=0.0               ! XX/17 attachment point for layer types C, CB (enter 0 for other types)

      DedType='   '               ! 10/18 deductible type: NO, AP, BL, FR, MA, MA2, MM, MM2, MI, MI2, PL (up to 3 characters)
      DedAmt1=0.0                 ! 11/19 deductible amount 1: minimum for types MM, MM2, MI, MI2; maximum for MA, MA2; blanket deduc for BL, FR, percentage for PL
      DedAmt2=0.0                 ! 12/20 deductible amount 2: maximum for types MM, MM2
      Reinst=0                    ! 13/21 maximum number of reinstatements (reserved for future use, enter 0)

      ReinsCount=0                ! 14/22 number of ceded reinsurance contracts that protect this layer (if none enter 0 and stop parsing record; otherwise, repeat fields 23-29 for each contract)
      ReinsOrder(1:maxre)=0                ! 15/23 reinsurance order
      ReinsType(1:maxre)='    '            ! 16/24 ceded reinsurance type (up to 4 characters): PFCP=proportional facultative as ceded %, PFCA=proportional facultative as ceded amount, NFG=non-proportional facultative in terms of insurers gross limit; SS=surplus share treaty
      ReinsCID(1:maxre)='                                '     ! 17/25 reinsurance certificate or program ID (up to 32 characters)
      ReinsField1(1:maxre)=0.0             ! 18/26 ceded reinsurance field 1 for types PFCP (fraction ceded), PFCA (amount ceded), NFG or SS (layer number of ceded excess)
      ReinsField2(1:maxre)=0.0             ! 19/27 ceded reinsurance field 2 for types NFG or SS (gross limit of the layer)
      ReinsField3(1:maxre)=0.0             ! 20/28 ceded reinsurance field 3 for types NFG or SS (attachment point of the layer) 
      ReinsField4(1:maxre)=0.0             ! 21/29 ceded reinsurance field 4 for types NFG or SS (fraction of the layer ceded)

	ivermajor=iversion/10
      rt_str='                    '
      ilen=LEN_TRIM(upx_str)

      istart=1
      do k=1,499
        do i=istart,ilen
          if (upx_str(i:i) .ne. ' ') goto 100
        end do
        return
 100    continue
        istart=i

        do i=istart,ilen
          if (upx_str(i:i) .eq. ',') then
            iend=i-1
            goto 200
	    else if (i .eq. ilen) then
            iend=ilen
            goto 200
	    end if
        end do
        return
 200    continue
        temp_str=upx_str(istart:iend)

        if (k .eq. 1) then
          if (temp_str(1:2) .eq. '61') then
            ParseLayerRecord=61                 ! 01 record type code (up to 4 characters)
          else
            ParseLayerRecord=0
          end if

        else if (k .eq. 2) then
          polid=upx_str(istart:iend)            ! 02 policy ID (up to 32 characters)

        else if (k .eq. 3) then
          layerid=upx_str(istart:iend)          ! 03 layer ID (up to 60 characters)

        else if (k .eq. 4) then
          Premium=StringToReal(temp_str)        ! 04 total premium received for this layer
          if (Premium .lt. 0.) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 5) then
          Peril=upx_str(istart:iend)            ! 05 layer peril code (up to 30 characters)

        else if (k .eq. 6) then
          LimitType=upx_str(istart:iend)        ! 06 layer limit type (up to 6 characters): B=blanket, E=excess, *** not supported *** C=limit by coverage, CB=combined limit for A+B+C with separate for D, CSL100=offshore, CSLAI=offshore
          if (LimitType .ne. 'B'      .and. LimitType .ne. 'E'     .and. 
     &        LimitType .ne. 'C'      .and. LimitType .ne. 'CB'    .and.
     &        LimitType .ne. 'CSL100' .and. LimitType .ne. 'CSLAI') then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 7) then
          Limit1=StringToReal(temp_str)         ! 07 layer limit field 1 for layer types B (total insured or "blanket" limit) or E (primary limit), CSL100 or CSLAI (layer limit) -- not use for layer types C or CB
          if (Limit1 .lt. 0.) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 8) then
          Limit2=StringToReal(temp_str)         ! 08 layer limit field 2 for layer types E or C (gross limit)
          if (Limit2 .lt. 0.) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 9) then
          AttachPt=StringToReal(temp_str)       ! 09 attachment point fo this layer
          if (AttachPt .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 10 .and. ivermajor .ge. 10) then
          LimitA=StringToReal(temp_str)         ! XX/10 layer limit field for layer types C, CB, CSL100, or CSLAI (enter 0 for types B and E)
          if (LimitA .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 11 .and. ivermajor .ge. 10) then
          LimitB=StringToReal(temp_str)         ! XX/11 layer limit field for layer types C, CSL100, or CSLAI (enter 0 for other types)
          if (LimitB .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 12 .and. ivermajor .ge. 10) then
          LimitC=StringToReal(temp_str)         ! XX/12 layer limit field for layer types C, CSL100, or CSLAI (enter 0 for other types)
          if (LimitC .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 13 .and. ivermajor .ge. 10) then
          LimitD=StringToReal(temp_str)         ! XX/13 layer limit field for layer types C, CB, CSL100, or CSLAI (enter 0 for types B and E)
          if (LimitD .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 14 .and. ivermajor .ge. 10) then
          AttachPtA=StringToReal(temp_str)      ! XX/14 attachment point for layer types C, CB (enter 0 for other types)
          if (AttachPtA .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 15 .and. ivermajor .ge. 10) then
          AttachPtB=StringToReal(temp_str)      ! XX/15 attachment point for layer type C (enter 0 for other types)
          if (AttachPtB .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 16 .and. ivermajor .ge. 10) then
          AttachPtC=StringToReal(temp_str)      ! XX/16 attachment point for layer type C (enter 0 for other types)
          if (AttachPtC .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if (k .eq. 17 .and. ivermajor .ge. 10) then
          AttachPtD=StringToReal(temp_str)      ! XX/17 attachment point for layer types C, CB (enter 0 for other types)
          if (AttachPtD .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if ((k .eq. 10 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 18 .and. ivermajor .ge. 10)) then
          DedType=upx_str(istart:iend)          ! 10/18 deductible type: NO, AP, BL, FR, MA, MA2, MM, MM2, MI, MI2, PL (up to 3 characters)
          if (DedType .ne. 'NO'  .and. DedType .ne. 'AP'  .and. 
     &        DedType .ne. 'BL'  .and. DedType .ne. 'FR'  .and.
     &        DedType .ne. 'MA'  .and. DedType .ne. 'MA2' .and.
     &        DedType .ne. 'MM'  .and. DedType .ne. 'MM2' .and.
     &        DedType .ne. 'MI'  .and. DedType .ne. 'MI2' .and.
     &        DedType .ne. 'PL') then
            ParseLayerRecord=-k
          end if

        else if ((k .eq. 11 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 19 .and. ivermajor .ge. 10)) then
          DedAmt1=StringToReal(temp_str)        ! 11/19 deductible amount 1: minimum for types MM, MM2, MI, MI2; maximum for MA, MA2; blanket deduc for BL, FR, percentage for PL
          if (DedAmt1 .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if ((k .eq. 12 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 20 .and. ivermajor .ge. 10)) then
          DedAmt2=StringToReal(temp_str)        ! 12/20 deductible amount 2: maximum for types MM, MM2
          if (DedAmt2 .lt. 0.0) then
            ParseLayerRecord=-k
          end if

        else if ((k .eq. 13 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 21 .and. ivermajor .ge. 10)) then
          Reinst=StringToInteger(temp_str)      ! 13/21 maximum number of reinstatements (reserved for future use, enter 0)
          if (Reinst .ne. 0) then
            ParseLayerRecord=-k
          end if

        else if ((k .eq. 14 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 22 .and. ivermajor .ge. 10)) then
          ReinsCount=StringToInteger(temp_str)    ! 14/22 number of ceded reinsurance contracts that protect this layer (if none enter 0 and stop parsing record; otherwise, repeat fields 23-29 for each contract)
          if (ReinsCount .lt. 0) then
            ParseLayerRecord=-k
          end if

        else if ((k .gt. 14 .and. ivermajor .eq. 9) .or. 
     &           (k .gt. 22 .and. ivermajor .ge. 10)) then
          if (ivermajor .eq. 9) then
	      kren=1+(k-14)/7
            krem=mod(k-14,7)
          else if (ivermajor .ge. 10) then
	      kren=1+(k-22)/7
            krem=mod(k-22,7)
	    else
            ParseLayerRecord=-k
	    end if

			if (kren .gt. ReinsCount) then
			  return
			end if

          if (krem .eq. 1) then
            ReinsOrder(kren)=StringToInteger(temp_str)  ! 15/23 reinsurance order
            if (ReinsOrder(kren) .lt. 0) then
              ParseLayerRecord=-k
            end if

          else if (krem .eq. 2) then
            ReinsType(kren)=upx_str(istart:iend)        ! 16/24 ceded reinsurance type (up to 4 characters): PFCP=proportional facultative as ceded %, PFCA=proportional facultative as ceded amount, NFG=non-proportional facultative in terms of insurers gross limit; SS=surplus share treaty
            if (ReinsType(kren) .ne. 'PFCP' .and. 
     &          ReinsType(kren) .ne. 'PFCA' .and. 
     &          ReinsType(kren) .ne. 'NFG'  .and. 
     &          ReinsType(kren) .ne. 'SS') then
              ParseLayerRecord=-k
            end if

          else if (krem .eq. 3) then
            ReinsCID(kren)=upx_str(istart:iend)         ! 17/25 reinsurance certificate or program ID (up to 32 characters)

          else if (krem .eq. 4) then
            ReinsField1(kren)=StringToReal(temp_str)    ! 18/26 ceded reinsurance field 1 for types PFCP (fraction ceded), PFCA (amount ceded), NFG or SS (layer number of ceded excess)
            if (ReinsField1(kren) .lt. 0.0) then
              ParseLayerRecord=-k
            end if

          else if (krem .eq. 5) then
            ReinsField2(kren)=StringToReal(temp_str)    ! 19/27 ceded reinsurance field 2 for types NFG or SS (gross limit of the layer)
            if (ReinsField2(kren) .lt. 0.0) then
              ParseLayerRecord=-k
            end if

          else if (krem .eq. 6) then
            ReinsField3(kren)=StringToReal(temp_str)    ! 20/28 ceded reinsurance field 3 for types NFG or SS (attachment point of the layer) 
            if (ReinsField3(kren) .lt. 0.0) then
              ParseLayerRecord=-k
            end if

          else if (krem .eq. 7) then
            ReinsField4(kren)=StringToReal(temp_str)    ! 21/29 ceded reinsurance field 4 for types NFG or SS (fraction of the layer ceded)
            if (ReinsField4(kren) .lt. 0.0) then
              ParseLayerRecord=-k
            end if

	    end if

        end if
        istart=iend+2
      end do

      return
      end
!
!******************************************************************************
!
      integer function ParseSublimitRecord(upx_str,iversion,polid,
     &        layerid,AreaCode,Peril,LimitType,Limit1,Limit2,
     &        LimitA,LimitB,LimitC,LimitD,AttachPt,
     &        AttachPtA,AttachPtB,AttachPtC,AttachPtD,
     &        DedType,DedAmt1,DedAmt2,Reinst)
!
!     returns field values of a Unicede/px sublimit record;
!     if the record type is 62 (sublimit record), the return value is 62;
!     otherwise, the return value is zero.
!
!     Versions 9.x -- 13 fields
!     Versions 10.x -- 17 fields (inserts fields 9-12)
!     Versions 11.x, 12.x, 13.x, 14.x -- 21 fields (inserts fields 14-17)
!
!     First 8 fields are the same in all versions
!
!******************************************************************************
!
      implicit none

      character*(*) upx_str       ! upx location record string
	integer iversion            ! upx file verion x 10 (must be 90, 95, 100, 105, 110, 115, 120, 125, 130 or 140)

      character*(*) polid         ! 02 policy ID (up to 32 characters)
      character*(*) layerid       ! 03 layer ID (up to 60 characters)
      character*(*) AreaCode      ! 04 sublimit area code (up to 20 characters)
      character*(*) Peril         ! 05 sublimit peril code (up to 30 characters)
      character*(*) LimitType     ! 06 sublimit type (up to 6 characters): B=blanket, E=excess, *** not supported *** C=limit by coverage, CB=combined limit for A+B+C with separate for D, CSL100=offshore, CSLAI=offshore
      real Limit1                 ! 07 sublimit field 1 for sublimit types B or E
      real Limit2                 ! 08 sublimit field 2 for sublimit type E
      real LimitA                 ! XX/09/09 sublimit field for sublimit types C, CB, CSL100, or CSLAI
      real LimitB                 ! XX/10/10 sublimit field for sublimit types 
      real LimitC                 ! XX/11/11 sublimit field for sublimit types C, CSL100, or CSLAI
      real LimitD                 ! XX/12/12 sublimit field for sublimit types C, CB, CSL100, or CSLAI
      real AttachPt               ! 09/13/13 attachment point for sublimit types B or E
      real AttachPtA              ! XX/XX/14 attachment point for sublimit types C, CB, CSL100, or CSLAI
      real AttachPtB              ! XX/XX/15 attachment point for sublimit types C, CSL100, or CSLAI
      real AttachPtC              ! XX/XX/16 attachment point for sublimit types C, CSL100, or CSLAI
      real AttachPtD              ! XX/XX/17 attachment point for sublimit types C, CB, CSL100, or CSLAI
      character*(*) DedType       ! 10/14/18 deductible type: NO, MM, MM2, MI, MI2, MA, MA2 (up to 3 characters)
      real DedAmt1                ! 11/15/19 deductible amount 1: minimum for types MM, MM2, MI, MI2; maximum for MA, MA2
      real DedAmt2                ! 12/16/20 deductible amount 2: maximum for types MM, MM2
      integer Reinst              ! 13/17/21 maximum number of reinstatements (reserved for future use, enter 0)
!
! local variables
!
      character*20 rt_str
      character*100 temp_str
      integer ilen
      integer k
      integer i
      integer istart
      integer iend
      integer klen
	integer ivermajor
      integer StringToInteger
      real StringToReal
!
! initializations
!
      ParseSublimitRecord=0
      polid=    '                                '    ! 02 policy ID (up to 32 characters)
      layerid=  '                              '//
     &          '                              '      ! 03 layer ID (up to 60 characters)
      AreaCode= '                    '                ! 04 sublimit area code (up to 20 characters)
      Peril=    '                              '      ! 05 sublimit peril code (up to 30 characters)
      LimitType='    '            ! 06 sublimit type (up to 6 characters): B=blanket, E=excess, *** not supported *** C=limit by coverage, CB=combined limit for A+B+C with separate for D, CSL100=offshore, CSLAI=offshore
      Limit1=0.0                  ! 07 sublimit field 1 for sublimit types B or E
      Limit2=0.0                  ! 08 sublimit field 2 for sublimit type E
      LimitA=0.0                  ! XX/09/09 sublimit field for sublimit types C, CB, CSL100, or CSLAI
      LimitB=0.0                  ! XX/10/10 sublimit field for sublimit types 
      LimitC=0.0                  ! XX/11/11 sublimit field for sublimit types C, CSL100, or CSLAI
      LimitD=0.0                  ! XX/12/12 sublimit field for sublimit types C, CB, CSL100, or CSLAI
      AttachPt=0.0                ! 09/13/13 attachment point for sublimit types B or E
      AttachPtA=0.0               ! XX/XX/14 attachment point for sublimit types C, CB, CSL100, or CSLAI
      AttachPtB=0.0               ! XX/XX/15 attachment point for sublimit types C, CSL100, or CSLAI
      AttachPtC=0.0               ! XX/XX/16 attachment point for sublimit types C, CSL100, or CSLAI
      AttachPtD=0.0               ! XX/XX/17 attachment point for sublimit types C, CB, CSL100, or CSLAI
      DedType='   '               ! 10/14/18 deductible type: NO, MM, MM2, MI, MI2, MA, MA2 (up to 3 characters)
      DedAmt1=0.0                 ! 11/15/19 deductible amount 1: minimum for types MM, MM2, MI, MI2; maximum for MA, MA2
      DedAmt2=0.0                 ! 12/16/20 deductible amount 2: maximum for types MM, MM2
      Reinst=0                    ! 13/17/21 maximum number of reinstatements (reserved for future use, enter 0)

	ivermajor=iversion/10
      rt_str='                    '
      ilen=LEN_TRIM(upx_str)

      istart=1
      do k=1,21
        do i=istart,ilen
          if (upx_str(i:i) .ne. ' ') goto 100
        end do
        return
 100    continue
        istart=i

        do i=istart,ilen
          if (upx_str(i:i) .eq. ',') then
            iend=i-1
            goto 200
	    else if (k .eq. 21 .and. i .eq. ilen) then
            iend=ilen
            goto 200
	    end if
        end do
        return
 200    continue
        temp_str=upx_str(istart:iend)

        if (k .eq. 1) then
          if (temp_str(1:2) .eq. '62') then
            ParseSublimitRecord=62              ! 01 record type code (up to 4 characters)
          else
            ParseSublimitRecord=0
          end if

        else if (k .eq. 2) then
          polid=upx_str(istart:iend)            ! 02 policy ID (up to 32 characters)

        else if (k .eq. 3) then
          layerid=upx_str(istart:iend)          ! 03 layer ID (up to 60 characters)

        else if (k .eq. 4) then
          AreaCode=upx_str(istart:iend)         ! 04 sublimit area code (up to 20 characters)

        else if (k .eq. 5) then
          Peril=upx_str(istart:iend)            ! 05 sublimit peril code (up to 30 characters)

        else if (k .eq. 6) then
          LimitType=upx_str(istart:iend)        ! 06 sublimit type (up to 6 characters): B=blanket, E=excess, *** not supported *** C=limit by coverage, CB=combined limit for A+B+C with separate for D, CSL100=offshore, CSLAI=offshore
          if (LimitType .ne. 'B'      .and. LimitType .ne. 'E'     .and. 
     &        LimitType .ne. 'C'      .and. LimitType .ne. 'CB'    .and.
     &        LimitType .ne. 'CSL100' .and. LimitType .ne. 'CSLAI') then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 7) then
          Limit1=StringToReal(temp_str)         ! 07 sublimit field 1 for sublimit types B or E
          if (Limit1 .lt. 0.) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 8) then
          Limit2=StringToReal(temp_str)         ! 08 sublimit field 2 for sublimit type E
          if (Limit2 .lt. 0.) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 9 .and. ivermajor .ge. 10) then
          LimitA=StringToReal(temp_str)         ! XX/09/09 sublimit field for sublimit types C, CB, CSL100, or CSLAI
          if (LimitA .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 10 .and. ivermajor .ge. 10) then
          LimitB=StringToReal(temp_str)         ! XX/10/10 sublimit field for sublimit types C, CSL100, or CSLAI
          if (LimitB .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 11 .and. ivermajor .ge. 10) then
          LimitC=StringToReal(temp_str)         ! XX/11/11 sublimit field for sublimit types C, CSL100, or CSLAI
          if (LimitC .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 12 .and. ivermajor .ge. 10) then
          LimitD=StringToReal(temp_str)         ! XX/12/12 sublimit field for sublimit types C, CB, CSL100, or CSLAI
          if (LimitD .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if ((k .eq. 9 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 13 .and. ivermajor .ge. 10)) then
          AttachPt=StringToReal(temp_str)       ! 09/13/13 attachment point for sublimit types B or E
          if (AttachPt .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 14 .and. ivermajor .ge. 11) then
          AttachPt=StringToReal(temp_str)       ! XX/XX/14 attachment point for sublimit types C, CB, CSL100, or CSLAI
          if (AttachPtA .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 15 .and. ivermajor .ge. 11) then
          AttachPt=StringToReal(temp_str)       ! XX/XX/15 attachment point for sublimit types C, CSL100, or CSLAI
          if (AttachPtB .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 16 .and. ivermajor .ge. 11) then
          AttachPt=StringToReal(temp_str)       ! XX/XX/16 attachment point for sublimit types C, CSL100, or CSLAI
          if (AttachPtC .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if (k .eq. 17 .and. ivermajor .ge. 11) then
          AttachPt=StringToReal(temp_str)       ! XX/XX/17 attachment point for sublimit types C, CB, CSL100, or CSLAI
          if (AttachPtD .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if ((k .eq. 10 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 14 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 18 .and. ivermajor .ge. 11)) then
          DedType=upx_str(istart:iend)          ! 10/14/18 deductible type: NO, MM, MM2, MI, MI2, MA, MA2 (up to 3 characters)
          if (DedType .ne. 'NO'  .and. DedType .ne. 'MM' .and. 
     &        DedType .ne. 'MM2' .and. DedType .ne. 'MI' .and.
     &        DedType .ne. 'MI2' .and. DedType .ne. 'MA' .and.
     &        DedType .ne. 'MA2') then
            ParseSublimitRecord=-k
          end if

        else if ((k .eq. 11 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 15 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 19 .and. ivermajor .ge. 11)) then
          DedAmt1=StringToReal(temp_str)        ! 11/15/19 deductible amount 1: minimum for types MM, MM2, MI, MI2; maximum for MA, MA2
          if (DedAmt1 .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if ((k .eq. 12 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 16 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 20 .and. ivermajor .ge. 11)) then
          DedAmt2=StringToReal(temp_str)        ! 12/16/20 deductible amount 2: maximum for types MM, MM2
          if (DedAmt2 .lt. 0.0) then
            ParseSublimitRecord=-k
          end if

        else if ((k .eq. 13 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 17 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 21 .and. ivermajor .ge. 11)) then
          Reinst=StringToInteger(temp_str)      ! 13/17/21 maximum number of reinstatements (reserved for future use, enter 0)
          if (Reinst .ne. 0) then
            ParseSublimitRecord=-k
          end if

        end if
        istart=iend+2
      end do

      return
      end
!
!******************************************************************************
!
      integer function ParseLocationRecord(upx_str,iversion,polid,locid,
     &        AreaScheme,StateFIPS,CountyFIPS,ZIP5,GeoLat,GeoLong,
     &        RiskCount,RepValBldg,RepValOStr,RepValCont,RepValTime,
     &        RVDaysCovered,ConType,ConBldg,ConOStr,OccType,Occ,
     &        YearBuilt,Stories,GrossArea,PerilCount,Peril,LimitType,
     &        Limits,Participation,DedType,Deds,territory,SubArea,
     &        ReinsCount,ReinsOrder,ReinsType,ReinsCID,
     &        ReinsField1,ReinsField2,ReinsField3,ReinsField4)
!
!     returns field values of a Unicede/px location record;
!     if the record type is 63 (location record), the return value is 63;
!     otherwise, the return value is zero.
!
!     Versions 9.x -- 57 fields
!     Versions 10.x -- 58 fields (inserts field 43 -- Participation)
!     Versions 11.0 -- 59 fields (inserts field 44 -- Participation2)
!     Versions 11.5, 12.x, 13.x, 14.x -- 60 fields (inserts field 04 -- ISO building ID number (ISOBIN))
!
!     First 3 fields are the same in all versions
!
!******************************************************************************
!
      implicit none

	integer, parameter :: maxre=5 ! maximum number of ceded reinsurance contracts that protect any one layer

      character*(*) upx_str       ! upx location record string
	integer iversion            ! upx file verion x 10 (must be 90, 95, 100, 105, 110, 115, 120, 125, 130, or 140)

      character*(*) polid         ! 02/02/02/02 policy ID (up to 32 characters)
      character*(*) locid         ! 03/03/03/03 location ID (up to 60 characters)
      character*(60) ISOBIN       ! xx/xx/xx/04 ISO building ID number (up to ** characters)
      character*(60) name         ! 04/04/04/05 location name (up to 60 characters)
      character*(60) address      ! 05/05/05/06 location street address (up to 60 characters)
      character*(60) city         ! 06/06/06/07 location city (up to 60 characters)
      integer AreaScheme          ! 07/07/07/08 type of area codes; must be 1003 (ZIP5) or 1008 (ZIP9)
      integer StateFIPS           ! 08/08/08/09 area (2-digit state FIPS)
      integer CountyFIPS          ! 09/09/09/10 subArea (3-digit county FIPS)
      integer ZIP5                ! 10/10/10/11 postalArea (5-digit ZIP Code)
      integer country							! 11/11/11/12 country code (US=1)
      real GeoLat                 ! 12/12/12/13 latitude (degrees North; south is negative)
      real GeoLong                ! 13/13/13/14 longitude (degrees East; west is negative)
      integer RiskCount           ! 18/18/18/19 number of risks (positive integer)
      real RepValBldg             ! 19/19/19/20 total replacement value of the building(s) or ITV if value given is between 0 and 1
      real RepValOStr             ! 20/20/20/21 total replacement value of other structures or ITV if value given is between 0 and 1
      real RepValCont             ! 21/21/21/22 sum of replacement values or ACVs of the contents or ITV if value given is between 0 and 1
      real RepValTime             ! 22/22/22/23 total time element coverage for a period of RVDaysCovered
      real RVDaysCovered          ! 23/23/23/24 number of days represented by the value in RepValTime
      character*(*) ConType       ! 25/25/25/26 construction code source: AIR, ITC, ISE, ISF, ISW, RMI, or RMS
      integer ConBldg             ! 26/26/26/27 construction class (*** are non-AIR classes coded as integers? ***)
      integer ConOStr             ! 27/27/27/28 construction class (*** are non-AIR classes coded as integers? ***)
      character*(*) OccType       ! 29/29/29/30 occupancy code source: AIR, ITC, ISB, ISC, ISO, RMI, RMS, RWC, SIC
      integer Occ                 ! 30/30/30/31 occupancy class (*** are non-AIR classes coded as integers? ***)
      integer YearBuilt           ! 31/31/31/32 year built or year of last major upgrade
      real Stories                ! 32/32/32/33 number of floors
      real GrossArea              ! 35/35/35/36 total area of the building, in square feet or square meters (???)
      integer PerilCount					! 36/36/36/37 number perils for which insurance terms are unique
      character*30 Peril          ! 37/37/37/38 peril code (up to 30 characters)
      character*1 LimitType       ! 38/38/38/39 limit type: N=none (see layer record), C=by coverage, S=sum of coverages
      real Limits(4)              ! 39/39/39/40 building or site limit
															! 40/40/40/41 other structures limit 
															! 41/41/41/42 contents limit 
															! 42/42/42/43 time element limit 
      real Participation          ! xx/43/43/44 fraction of risk covered by the insurer (0.0 to 1.0)
      real Participation2         ! xx/xx/44/45 fraction of risk owned by the insured party or working interest (0.0 to 1.0)
      character*2 DedType         ! 43/44/45/46 deductible type: NO, BA, BP, CA, CP, DA, DP, FR, MA, ML, MP, SA, SP, SL, AA
      real Deds(4)                ! 44/45/46/47 building or site deductible
															! 45/46/47/48 other structures deductible (SA,SP,C*,D*,B*) or fraction of A+B+C loss (ML)
															! 46/47/48/49 contents deductible (SA,SP,C*,D*,B*)
															! 47/48/49/50 time element deductible (SA,SP,C*,D*,ML)
      character*30 territory			! 48/49/50/51 user defined territory (up to 30 characters)
      character*30 subArea				! 49/50/51/52 user defined sublimit area code (up to 30 characters)

      integer ReinsCount          ! 50/51/52/53 number of ceded reinsurance contracts that protect this location (if none enter 0 and stop parsing record; otherwise, repeat fields 23-29 for each contract)
      integer ReinsOrder(maxre)     ! 51/52/53/54 reinsurance order
      character*4 ReinsType(maxre)  ! 52/53/54/55 ceded reinsurance type (up to 4 characters): PFCP=proportional facultative as ceded %, PFCA=proportional facultative as ceded amount, NFG=non-proportional facultative in terms of insurers gross limit; SS=surplus share treaty
      character*32 ReinsCID(maxre)  ! 53/54/55/56 reinsurance certificate or program ID (up to 32 characters)
      real ReinsField1(maxre)       ! 54/55/56/57 ceded reinsurance field 1 for types PFCP (fraction ceded), PFCA (amount ceded), NFG or SS (layer number of ceded excess)
      real ReinsField2(maxre)       ! 55/56/57/58 ceded reinsurance field 2 for types NFG or SS (gross limit of the layer)
      real ReinsField3(maxre)       ! 56/57/58/59 ceded reinsurance field 3 for types NFG or SS (attachment point of the layer) 
      real ReinsField4(maxre)       ! 57/58/59/60 ceded reinsurance field 4 for types NFG or SS (fraction of the layer ceded)
!
! local variables
!
      character*20 rt_str
      character*100 temp_str
      integer ilen
      integer k
      integer i
      integer istart
      integer iend
      integer klen
	integer ivermajor
      integer StringToInteger
      real StringToReal
	integer kren
	integer krem
!
! initializations
!
      ParseLocationRecord=0
      polid='                                '         ! 02/02/02/02 policy ID (up to 32 characters)
      locid='                              '//
     &      '                              '           ! 03/03/03/03 location ID (up to 60 characters)
      AreaScheme=0                ! 07/07/07/08 type of area codes; must be 1003 (ZIP5) or 1008 (ZIP9)
      StateFIPS=0                 ! 08/08/08/09 area (2-digit state FIPS)
      CountyFIPS=0                ! 09/09/09/10 subArea (3-digit county FIPS)
      ZIP5=0                      ! 10/10/10/11 postalArea (5-digit ZIP Code)
      GeoLat=0.00                 ! 12/12/12/13 latitude (degrees North; south is negative)
      GeoLong=0.00                ! 13/13/13/14 longitude (degrees East; west is negative)
      RiskCount=1                 ! 18/18/18/19 number of risks (positive integer)
      RepValBldg=0.00             ! 19/19/19/20 total replacement value of the building(s) or ITV if value given is between 0 and 1
      RepValOStr=0.00             ! 20/20/20/21 total replacement value of other structures or ITV if value given is between 0 and 1
      RepValCont=0.00             ! 21/21/21/22 sum of replacement values or ACVs of the contents or ITV if value given is between 0 and 1
      RepValTime=0.00             ! 22/22/22/23 total time element coverage for a period of RVDaysCovered
      RVDaysCovered=0.00          ! 23/23/23/24 number of days represented by the value in RepValTime
      ConType='AIR'               ! 25/25/25/26 construction code source: AIR, ITC, ISE, ISF, ISW, RMI, or RMS
      ConBldg=0										! 26/26/26/27 construction class (*** are non-AIR classes coded as integers? ***)
      ConOStr=0										! 27/27/27/28 construction class (*** are non-AIR classes coded as integers? ***)
      OccType='AIR'               ! 29/29/29/30 occupancy code source: AIR, ITC, ISB, ISC, ISO, RMI, RMS, RWC, SIC
      Occ=0												! 30/30/30/31 occupancy class (*** are non-AIR classes coded as integers? ***)
      YearBuilt=0                 ! 31/31/31/32 year built or year of last major upgrade
      Stories=0.00                ! 32/32/32/33 number of floors
      GrossArea=0.00              ! 35/35/35/36 total area of the building, in square feet or square meters (???)
	PerilCount=0								! 36/36/36/37 number perils for which insurance terms are unique
	Peril='                              '			! 37/37/37/38 peril code (up to 30 characters)
      LimitType=' '								! 38/38/38/39 limit type: N=none (see layer record), C=by coverage, S=sum of coverages
	Limits=0.0									! 39/39/39/40 building or site limit to 42/42/42/43 time element limit
	Participation=1.00          ! xx/43/43/44 fraction of risk covered by the insurer (0.0 to 1.0)
      Participation2=1.00         ! xx/xx/44/45 fraction of risk owned by the insured party or working interest (0.0 to 1.0)
      DedType='  '								! 43/44/45/46 deductible type: NO, BA, BP, CA, CP, DA, DP, FR, MA, ML, MP, SA, SP, SL, AA
      Deds=0.0										! 44/45/46/47 building or site deductible to 47/48/49/50 time element deductible (SA,SP,C*,D*,ML)
      territory='                              '	! 48/49/50/51 user defined territory (up to 30 characters)
      subArea=  '                              '	! 49/50/51/52 user defined sublimit area code (up to 30 characters)

      ReinsCount=0                ! 50/51/52/53 number of ceded reinsurance contracts that protect this location (if none enter 0 and stop parsing record; otherwise, repeat fields 23-29 for each contract)
      ReinsOrder(1:maxre)=0                ! 51/52/53/54 reinsurance order
      ReinsType(1:maxre)='    '            ! 52/53/54/55 ceded reinsurance type (up to 4 characters): PFCP=proportional facultative as ceded %, PFCA=proportional facultative as ceded amount, NFG=non-proportional facultative in terms of insurers gross limit; SS=surplus share treaty
      ReinsCID(1:maxre)='                                '     ! 53/54/55/56 reinsurance certificate or program ID (up to 32 characters)
      ReinsField1(1:maxre)=0.0             ! 54/55/56/57 ceded reinsurance field 1 for types PFCP (fraction ceded), PFCA (amount ceded), NFG or SS (layer number of ceded excess)
      ReinsField2(1:maxre)=0.0             ! 55/56/57/58 ceded reinsurance field 2 for types NFG or SS (gross limit of the layer)
      ReinsField3(1:maxre)=0.0             ! 56/57/58/59 ceded reinsurance field 3 for types NFG or SS (attachment point of the layer) 
      ReinsField4(1:maxre)=0.0             ! 57/58/59/60 ceded reinsurance field 4 for types NFG or SS (fraction of the layer ceded)

	ivermajor=iversion/10
      rt_str='                    '
      ilen=LEN_TRIM(upx_str)

      istart=1
      do k=1,999
        do i=istart,ilen
          if (upx_str(i:i) .ne. ' ') goto 100
        end do
        return
 100    continue
        istart=i

        do i=istart,ilen
          if (upx_str(i:i) .eq. ',') then
            iend=i-1
            goto 200
	    else if (i .eq. ilen) then
            iend=ilen
            goto 200
	    end if
        end do
        return
 200    continue
        temp_str=upx_str(istart:iend)

        if (k .eq. 1) then
          if (temp_str(1:2) .eq. '63') then
            ParseLocationRecord=63							! 02/02/02/02 policy ID (up to 32 characters)
          else
            ParseLocationRecord=0
				goto 900
          end if

        else if (k .eq. 2) then
          polid=upx_str(istart:iend)						! 03/03/03/03 location ID (up to 60 characters)

        else if (k .eq. 3) then
          locid=upx_str(istart:iend)

!        else if (k .eq. 4) then
!          iSeed=StringToInteger(temp_str)
!	    if (iSeed .lt. 0) then
!            iSeed=0
!	    end if

        else if ((k .eq. 7 .and. iversion .lt. 115) .or.
     &					 (k .eq. 8 .and. iversion .ge. 115)) then
          AreaScheme=StringToInteger(temp_str)	! 07/07/07/08 type of area codes; must be 1003 (ZIP5) or 1008 (ZIP9)
          if (AreaScheme .ne. 1003 .and.
     &        AreaScheme .ne. 1008) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 8 .and. iversion .lt. 115) .or.
     &					 (k .eq. 9 .and. iversion .ge. 115)) then
          StateFIPS=StringToInteger(temp_str)		! 08/08/08/09 area (2-digit state FIPS)
          if (StateFIPS .ne.  1 .and. StateFIPS .ne.  9 .and.		! AL, CT
     &        StateFIPS .ne. 10 .and. StateFIPS .ne. 11 .and.		! DE, DC
     &        StateFIPS .ne. 12 .and. StateFIPS .ne. 13 .and.		! FL, GA
     &        StateFIPS .ne. 22 .and. StateFIPS .ne. 23 .and.		! LA, ME
     &        StateFIPS .ne. 24 .and. StateFIPS .ne. 25 .and.		! MD, MA
     &        StateFIPS .ne. 28 .and. StateFIPS .ne. 33 .and.		! MS, NH
     &        StateFIPS .ne. 34 .and. StateFIPS .ne. 36 .and.		! NJ, NY
     &        StateFIPS .ne. 37 .and. StateFIPS .ne. 42 .and.		! NC, PA
     &        StateFIPS .ne. 44 .and. StateFIPS .ne. 45 .and.		! RI, SSC
     &        StateFIPS .ne. 48 .and. StateFIPS .ne. 50 .and.		! TX, VT
     &        StateFIPS .ne. 51 .and. StateFIPS .ne. 54) then		! VA, WV
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 9 .and. iversion .lt. 115) .or.
     &					 (k .eq. 10 .and. iversion .ge. 115)) then
          CountyFIPS=StringToInteger(temp_str)	! 09/09/09/10 subArea (3-digit county FIPS)
          if (CountyFIPS .eq. -99999) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 10 .and. iversion .lt. 115) .or.
     &					 (k .eq. 11 .and. iversion .ge. 115)) then
          klen=LEN_TRIM(temp_str)								! 10/10/10/11 postalArea (5-digit ZIP Code)
          if (AreaScheme .eq. 1008) then				! convert ZIP9 to ZIP5
!          if (klen .eq. 10 .and. temp_str(6:6) .eq. '-') then     
            temp_str(6:10)='     '
	      AreaScheme=1003
          end if
          ZIP5=StringToInteger(temp_str)
          if (ZIP5 .eq. -99999) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 12 .and. iversion .lt. 115) .or.
     &					 (k .eq. 13 .and. iversion .ge. 115)) then
          GeoLat=StringToReal(temp_str)					! 12/12/12/13 latitude (degrees North; south is negative)
          if (GeoLat .lt. -90. .or. GeoLat .gt. 90.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 13 .and. iversion .lt. 115) .or.
     &					 (k .eq. 14 .and. iversion .ge. 115)) then
          GeoLong=StringToReal(temp_str)				! 13/13/13/14 longitude (degrees East; west is negative)
          if (GeoLong .lt. -180. .or. GeoLong .gt. 180.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 18 .and. iversion .lt. 115) .or.
     &					 (k .eq. 19 .and. iversion .ge. 115)) then
          RiskCount=StringToInteger(temp_str)		! 18/18/18/19 number of risks (positive integer)
          if (RiskCount .eq. -99999) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 19 .and. iversion .lt. 115) .or.
     &					 (k .eq. 20 .and. iversion .ge. 115)) then
          RepValBldg=StringToReal(temp_str)			! 19/19/19/20 total replacement value of the building(s) or ITV if value given is between 0 and 1
          if (RepValBldg .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 20 .and. iversion .lt. 115) .or.
     &					 (k .eq. 21 .and. iversion .ge. 115)) then
          RepValOStr=StringToReal(temp_str)			! 20/20/20/21 total replacement value of other structures or ITV if value given is between 0 and 1
          if (RepValOStr .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 21 .and. iversion .lt. 115) .or.
     &					 (k .eq. 22 .and. iversion .ge. 115)) then
          RepValCont=StringToReal(temp_str)			! 21/21/21/22 sum of replacement values or ACVs of the contents or ITV if value given is between 0 and 1
          if (RepValCont .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 22 .and. iversion .lt. 115) .or.
     &					 (k .eq. 23 .and. iversion .ge. 115)) then
          RepValTime=StringToReal(temp_str)			! 22/22/22/23 total time element coverage for a period of RVDaysCovered
          if (RepValTime .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 23 .and. iversion .lt. 115) .or.
     &					 (k .eq. 24 .and. iversion .ge. 115)) then
          RVDaysCovered=StringToReal(temp_str)	! 23/23/23/24 number of days represented by the value in RepValTime
          if (RVDaysCovered .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 25 .and. iversion .lt. 115) .or.
     &					 (k .eq. 26 .and. iversion .ge. 115)) then
          ConType=upx_str(istart:iend)					! 25/25/25/26 construction code source: AIR, ITC, ISE, ISF, ISW, RMI, or RMS

        else if ((k .eq. 26 .and. iversion .lt. 115) .or.
     &					 (k .eq. 27 .and. iversion .ge. 115)) then
          ConBldg=StringToInteger(temp_str)			! 26/26/26/27 construction class (*** are non-AIR classes coded as integers? ***)
          if (ConBldg .lt. 0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 27 .and. iversion .lt. 115) .or.
     &					 (k .eq. 28 .and. iversion .ge. 115)) then
          ConOStr=StringToInteger(temp_str)			! 27/27/27/28 construction class (*** are non-AIR classes coded as integers? ***)
          if (ConOStr .lt. 0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 29 .and. iversion .lt. 115) .or.
     &					 (k .eq. 30 .and. iversion .ge. 115)) then
          OccType=upx_str(istart:iend)					! 29/29/29/30 occupancy code source: AIR, ITC, ISB, ISC, ISO, RMI, RMS, RWC, SIC

        else if ((k .eq. 30 .and. iversion .lt. 115) .or.
     &					 (k .eq. 31 .and. iversion .ge. 115)) then
          Occ=StringToInteger(temp_str)					! 30/30/30/31 occupancy class (*** are non-AIR classes coded as integers? ***)
          if (Occ .lt. 0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 31 .and. iversion .lt. 115) .or.
     &					 (k .eq. 32 .and. iversion .ge. 115)) then
          YearBuilt=StringToInteger(temp_str)		! 31/31/31/32 year built or year of last major upgrade
          if (YearBuilt .lt. 0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 32 .and. iversion .lt. 115) .or.
     &					 (k .eq. 33 .and. iversion .ge. 115)) then
          Stories=StringToReal(temp_str)				! 32/32/32/33 number of floors
          if (Stories .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 35 .and. iversion .lt. 115) .or.
     &					 (k .eq. 36 .and. iversion .ge. 115)) then
          GrossArea=StringToReal(temp_str)			! 35/35/35/36 total area of the building, in square feet or square meters (???)
          if (GrossArea .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 36 .and. iversion .lt. 115) .or.
     &					 (k .eq. 37 .and. iversion .ge. 115)) then
          PerilCount=StringToInteger(temp_str)	! 36/36/36/37 number perils for which insurance terms are unique
          if (PerilCount .lt. 0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 37 .and. iversion .lt. 115) .or.
     &					 (k .eq. 38 .and. iversion .ge. 115)) then
          Peril=upx_str(istart:iend)						! 37/37/37/38 peril code (up to 30 characters)

        else if ((k .eq. 38 .and. iversion .lt. 115) .or.
     &					 (k .eq. 39 .and. iversion .ge. 115)) then
          LimitType=upx_str(istart:istart)			! 38/38/38/39 limit type: N=none (see layer record), C=by coverage, S=sum of coverages
          if (iend .gt. istart) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 39 .and. iversion .lt. 115) .or.
     &					 (k .eq. 40 .and. iversion .ge. 115)) then
          Limits(1)=StringToReal(temp_str)			! 39/39/39/40 building or site limit
          if (Limits(1) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 40 .and. iversion .lt. 115) .or.
     &					 (k .eq. 41 .and. iversion .ge. 115)) then
          Limits(2)=StringToReal(temp_str)			! 40/40/40/41 other structures limit 
          if (Limits(2) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 41 .and. iversion .lt. 115) .or.
     &					 (k .eq. 42 .and. iversion .ge. 115)) then
          Limits(3)=StringToReal(temp_str)			! 41/41/41/42 contents limit 
          if (Limits(3) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 42 .and. iversion .lt. 115) .or.
     &					 (k .eq. 43 .and. iversion .ge. 115)) then
          Limits(4)=StringToReal(temp_str)			! 42/42/42/43 time element limit 
          if (Limits(4) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 43 .and. ivermajor .eq. 10) .or.
     &					 (k .eq. 43 .and. iversion .eq. 110) .or. 
     &					 (k .eq. 44 .and. iversion .ge. 115)) then
          Participation=StringToReal(temp_str)	! xx/43/43/44 fraction of risk covered by the insurer (0.0 to 1.0)
          if (Participation .gt. 1.001 .or. Participation .lt. 0.0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 44 .and. iversion .eq. 110) .or. 
     &					 (k .eq. 45 .and. iversion .ge. 115)) then
          Participation2=StringToReal(temp_str)	! xx/xx/44/45 fraction of risk owned by the insured party or working interest (0.0 to 1.0)
          if (Participation2 .gt. 1.001 .or. Participation2.lt.0.0) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 43 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 44 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 45 .and. iversion .eq. 110) .or.
     &           (k .eq. 46 .and. iversion .ge. 115)) then
          DedType=upx_str(istart:istart+1)			! 43/44/45/46 deductible type: NO, BA, BP, CA, CP, DA, DP, FR, MA, ML, MP, SA, SP, SL, AA
          if (iend .gt. istart+1) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 44 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 45 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 46 .and. iversion .eq. 110) .or.
     &           (k .eq. 47 .and. iversion .ge. 115)) then
          Deds(1)=StringToReal(temp_str)				! 44/45/46/47 building or site deductible
          if (Deds(1) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 45 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 46 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 47 .and. iversion .eq. 110) .or.
     &           (k .eq. 48 .and. iversion .ge. 115)) then
          Deds(2)=StringToReal(temp_str)				! 45/46/47/48 other structures deductible (SA,SP,C*,D*,B*) or fraction of A+B+C loss (ML)
          if (Deds(2) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 46 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 47 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 48 .and. iversion .eq. 110) .or.
     &           (k .eq. 49 .and. iversion .ge. 115)) then
          Deds(3)=StringToReal(temp_str)				! 46/47/48/49 contents deductible (SA,SP,C*,D*,B*)
          if (Deds(3) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 47 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 48 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 49 .and. iversion .eq. 110) .or.
     &           (k .eq. 50 .and. iversion .ge. 115)) then
          Deds(4)=StringToReal(temp_str)				! 47/48/49/50 time element deductible (SA,SP,C*,D*,ML)
          if (Deds(4) .lt. 0.) then
            ParseLocationRecord=-k
          end if

        else if ((k .eq. 48 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 49 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 50 .and. iversion .eq. 110) .or.
     &           (k .eq. 51 .and. iversion .ge. 115)) then
          territory=upx_str(istart:iend)				! 48/49/50/51 user defined territory (up to 30 characters)

        else if ((k .eq. 49 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 50 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 51 .and. iversion .eq. 110) .or.
     &           (k .eq. 52 .and. iversion .ge. 115)) then
          subArea=upx_str(istart:iend)					! 49/50/51/52 user defined sublimit area code (up to 30 characters)

        else if ((k .eq. 50 .and. ivermajor .eq. 9) .or. 
     &           (k .eq. 51 .and. ivermajor .eq. 10) .or.
     &           (k .eq. 52 .and. iversion .eq. 110) .or.
     &           (k .eq. 53 .and. iversion .ge. 115)) then
          ReinsCount=StringToInteger(temp_str)	! 50/51/52/53 number of ceded reinsurance contracts that protect this location (if none enter 0 and stop parsing record; otherwise, repeat fields 23-29 for each contract)
          if (ReinsCount .lt. 0) then
            ParseLocationRecord=-k
          end if

        else if ((k .gt. 50 .and. ivermajor .eq. 9) .or. 
     &           (k .gt. 51 .and. ivermajor .eq. 10) .or.
     &           (k .gt. 52 .and. iversion .eq. 110) .or.
     &           (k .gt. 53 .and. iversion .ge. 115)) then
          if (ivermajor .eq. 9) then
	      kren=1+(k-50)/7
            krem=mod(k-50,7)
          else if (ivermajor .eq. 10) then
	      kren=1+(k-51)/7
            krem=mod(k-51,7)
          else if (iversion .eq. 110) then
	      kren=1+(k-52)/7
            krem=mod(k-52,7)
          else if (iversion .ge. 115) then
	      kren=1+(k-53)/7
            krem=mod(k-53,7)
	    else
            ParseLocationRecord=-k
	    end if

			if (kren .gt. ReinsCount) then
			  return
			end if

          if (krem .eq. 1) then
            ReinsOrder(kren)=StringToInteger(temp_str)  ! 51/52/53/54 reinsurance order
            if (ReinsOrder(kren) .lt. 0) then
              ParseLocationRecord=-k
            end if

          else if (krem .eq. 2) then
            ReinsType(kren)=upx_str(istart:iend)        ! 52/53/54/55 ceded reinsurance type (up to 4 characters): PFCP=proportional facultative as ceded %, PFCA=proportional facultative as ceded amount, NFG=non-proportional facultative in terms of insurers gross limit; SS=surplus share treaty
            if (ReinsType(kren) .ne. 'PFCP' .and. 
     &          ReinsType(kren) .ne. 'PFCA' .and. 
     &          ReinsType(kren) .ne. 'NFG'  .and. 
     &          ReinsType(kren) .ne. 'SS') then
              ParseLocationRecord=-k
            end if

          else if (krem .eq. 3) then
            ReinsCID(kren)=upx_str(istart:iend)         ! 53/54/55/56 reinsurance certificate or program ID (up to 32 characters)

          else if (krem .eq. 4) then
            ReinsField1(kren)=StringToReal(temp_str)    ! 54/55/56/57 ceded reinsurance field 1 for types PFCP (fraction ceded), PFCA (amount ceded), NFG or SS (layer number of ceded excess)
            if (ReinsField1(kren) .lt. 0.0) then
              ParseLocationRecord=-k
            end if

          else if (krem .eq. 5) then
            ReinsField2(kren)=StringToReal(temp_str)    ! 55/56/57/58 ceded reinsurance field 2 for types NFG or SS (gross limit of the layer)
            if (ReinsField2(kren) .lt. 0.0) then
              ParseLocationRecord=-k
            end if

          else if (krem .eq. 6) then
            ReinsField3(kren)=StringToReal(temp_str)    ! 56/57/58/59 ceded reinsurance field 3 for types NFG or SS (attachment point of the layer) 
            if (ReinsField3(kren) .lt. 0.0) then
              ParseLocationRecord=-k
            end if

          else if (krem .eq. 7) then
            ReinsField4(kren)=StringToReal(temp_str)    ! 57/58/59/60 ceded reinsurance field 4 for types NFG or SS (fraction of the layer ceded)
            if (ReinsField4(kren) .lt. 0.0) then
              ParseLocationRecord=-k
            end if

	    end if

        end if
        istart=iend+2
		if (istart .gt. ilen) goto 900
      end do

 900  continue
      return
      end
!
!******************************************************************************
!
      integer function ParseLocationDetailRecord(upx_str,iversion,
     &        polid64,locid64,
     &        IrFloorOfInterest,IrTreeExposure,IrSmallDebris,
     &        IrLargeDebris,IrTerrainRoughness,IrAdBldHeight,IrFFE,
     &        IrRoofGeometry,IrRoofPitch,IrRoofCover,IrRoofDeck,
     &        IrRoofCoverAttach,IrRoofDeckAttach,IrRoofAnchorage,
     &        IrRoofBuilt,IrWall,IrWallSiding,IrGlassType,
     &        IrGlassPercent,IrWindowProt,IrExteriorDoors,
     &        IrBldFndConn,IrFoundation,IrAttachStruct,IrAppurtStruct,
     &        IrMechSystem)
!
!     returns field values of a Unicede/px location record;
!     if the record type is 64 (location detail record), the return value is 64;
!     otherwise, the return value is zero.
!
!     Versions 9.0 through 11.5 -- 39 fields
!     Version 12.0 -- 49 fields (adds fields 40-49) -- Additional fields are currently ignored
!     Version 12.5 -- 56 fields (adds fields 50-56) -- Additional fields are currently ignored
!     Version 13.0 -- 58 fields (adds fields 57-58) -- Additional fields are currently ignored
!     Version 14.0 -- 60 fields (adds fields 59-60) -- Additional fields are currently ignored
!
!     First 39 fields are the same in all versions (except for change of name in field 7 from IrProximity to IrPounding in 12.0)
!
!******************************************************************************
!
      implicit none

      character*(*) upx_str       ! upx location record string
	integer iversion            ! upx file verion x 10 (must be 90, 95, 100, 105, 110, 115, 120, 125, 130 or 140)

      character*32 polid64        !  2 policy ID (up to 32 characters)
      character*60 locid64        !  3 location ID (up to 60 characters)
      integer IrFloorOfInterest   !  5 identifies floof of concern if coverage is not for entire building
      integer IrTreeExposure      !  8 tree hazard near building:           0=unknown, 1=no, 2=yes
      integer IrSmallDebris       !  9 small missile hazard within 200 ft:  0=unknown, 1=no, 2=yes
      integer IrLargeDebris       ! 10 large missile hazard within 200 ft:  0=unknown, 1=no, 2=yes
      integer IrTerrainRoughness  ! 11 terrain conditions near building:    0=unknown, 1=A, 2=B, 3=C (or HVHZ), 4=D
      integer IrAdBldHeight       ! 12 average height of adjacent buildings:0=unknown, N=number of stories
      
      integer IrFFE               ! 18 IrSpecial (special EQ-resistant systems) field used as back door to input First Floor Elevation
                                  ! For known FFE (w.r.t. NAVD88), then IrFFE=nint(10.*FFE+10000.) else IrFFE=0 (unknown) where FFE is in feet above (positive) or below (negative) NAVD88
                                  ! If (IrFFE>5000) then FFE=real(IrFFE-10000)/10. else FFE=-99. (unknown) 
                                  ! Example1: FFE=3.5 feet below NAVD88, then IrFFE=9965
                                  ! Example2: FFE=3.5 feet above NAVD88, then IrFFE=10035
                                  ! Example3: FFE=unknown, then IrFFE=0
      
      integer IrRoofGeometry      ! 20 roof shape:   0=unk, 1=flat, 2=unbr gable, 3=hip, 4=complex, 
                                  !                  5=stepped, 6=shed, 7=mansard, 8=br gable, 
                                  !                  9=pyramid, 10=gambrel
      integer IrRoofPitch         ! 21 roof slope:   0=unk, 1=low (<10deg), 2=med (10-30deg), 3=high (>30deg)
      integer IrRoofCover         ! 22 roof cover:   0=unk, 1=asphalt shingles, 2=wood shingles, 
                                  !                  3=clay/conc tiles, 4=metal panels, 5=slate, 
                                  !                  6=BUR w/ gravel, 7=SPM, 8=standing seam, 
                                  !                  9=BUR w/o gravel, 10=SPM ballasted, 11=FBC equiv.
	                            !                  ADDED: 12=FBC-Shingle, 13=FBC-Tile, 14=poured concrete
      integer IrRoofDeck          ! 23 roof deck:    0=unk, 1=plywood, 2=wood planks, 3=OSB/particle board,
                                  !                  4=metal deck with insulation board, 5=concrete on metal forms,
                                  !                  6=precast concrete, 7=reinf. concrete, 8=light metal
      integer IrRoofCoverAttach   ! 24 RC fasteners: 0=unk, 1=screws, 2=nails/staples, 3=adhesive/epoxy,
                                  !                  4=mortar
      integer IrRoofDeckAttach    ! 25 RD fasteners: 0=unk, 1=screws/bolts, 2=nails, 3=adhesive/epoxy,
                                  !                  4=structurally connected, 5=6d@6/12, 6=8d@6/12,
                                  !                  7=8d@6/6
      integer IrRoofAnchorage     ! 26 roof-wall:    0=unk, 1=hurricane ties, 2=nails/screws, 3=anchor bolts,
                                  !                  4=gravity, 5=adhesive/epoxy, 6=structurally connected,
                                  !                  7=clips, ADDED: 8=double wraps 
      integer IrRoofBuilt         ! 27 roof year:    0=unk, NNNN=year built/installed
      integer IrWall              ! 28 wall type:    0=unk, 1=brick/URM, 2=RM, 3=plywood, 4=wood planks,
                                  !                  5=OSB/particle board, 6=metal panels, 7=precast concrete,
                                  !                  8=cast-in-place concrete, 9=gypsum board
      integer IrWallSiding        ! 29 wall siding:  0=unk, 1=veneer brick/masonry, 2=wood shingles, 3=clapboards,
                                  !                  4=aluminum/vinyl siding, 5=stone panels, 6=EIFS, 7=stucco
      integer IrGlassType         ! 30 glass type:   0=unk, 1=annealed, 2=tempered, 3=heat strengthened,
                                  !                  4=laminated, 5=insulating glass units
      integer IrGlassPercent      ! 31 % wall area:  0=unk, 1=<5%, 2=5-20%, 3=20-60%, 4=>60%
      integer IrWindowProt        ! 32 protection:   0=unk, 1=none, 2=non-engineered (ARA ordinary), 3=engineered, ADDED: 4=basic, 5=plywood, 6=OSB
      integer IrExteriorDoors     ! 33 ext. doors    0=unk, 1=single width, 2=double width, 3=reinf. single,
                                  !                  4=reinf. double, 5=sliders, 6=reinf. sliders
      integer IrBldFndConn        ! 34 connection    0=unk, 1=hurricane ties, 2=nails/screws, 3=anchor bolts,
                                  !                  4=gravity, 5=adhesive/epoxy, 6=structurally connected
      
      integer IrFoundation        ! 35 Foundation   0= unknown/default, 1= Masonry basement, 2= concrete basement, 3= NOT USED
                                  !                 4= Crawlspace-cripple wall (wood), 5= Crawlspace-masonry (wood), 6= Post & Pier
                                  !                 7= Footing, 8= Mat/slab, 9=Pile, 10= No basement, 11= Engineering foundation, 
                                  !                 12= Crawlspace-raised (wood)   .....Added by ***DRM*** 11/19/2013
      
      integer IrAttachStruct      ! 37 attached str. 0=unk, 1=carports/canopies/porches, 2=single door garage,
                                  !                  3=double door garage, 4=reinf. single garage, 
                                  !                  5=reinf, double garage, 6=screened porches/glass patio doors,
                                  !                  7=balcony, 8=none
      integer IrAppurtStruct      ! 38 detached str. 0=unk, 1=detached garage, 2=pool enclosures, 3=shed,
                                  !                  4=masonry boundary wall, 5=other fence, 6=no appurt str,
                                  !                  7=no pool enclosures
      integer IrMechSystem        ! 39 roof top eq.  0=unk, 1=chimneys, 2=a/c units, 3=skylights, 4=parapets,
                                  !                  5=overhang/rake (8"-36"), 6=dormers, 7=other, 
                                  !                  8=no attached structures, 9=overhang/rake (<8"),
                                  !                  10=overhang/rake (>36"), 11=waterproof membrane/fabric,
                                  !                  12=SWR, 13=No SWR
!
! local variables
!
      character*20 rt_str
      character*100 temp_str
      integer ilen
      integer k
      integer i
      integer istart
      integer iend
      integer klen
	integer ivermajor
      integer StringToInteger
      real StringToReal
!
! initializations
!
      ParseLocationDetailRecord=0
      polid64='                                '         ! policy ID (up to 32 characters)
      locid64='                              '//
     &        '                              '           ! location ID (up to 60 characters)
      IrFloorOfInterest=0         !  5
      IrTreeExposure=0            !  8
      IrSmallDebris=0             !  9
      IrLargeDebris=0             ! 10
      IrTerrainRoughness=0        ! 11
      IrAdBldHeight=0             ! 12
      IrFFE=0                     ! 18 ***using IrSpecial (EQ-only) field as a back door for entering first floor elevation (FFE)***
      IrRoofGeometry=0            ! 20
      IrRoofPitch=0               ! 21
      IrRoofCover=0               ! 22
      IrRoofDeck=0                ! 23
      IrRoofCoverAttach=0         ! 24
      IrRoofDeckAttach=0          ! 25
      IrRoofAnchorage=0           ! 26
      IrRoofBuilt=0               ! 27
      IrWall=0                    ! 28
      IrWallSiding=0              ! 29
      IrGlassType=0               ! 30
      IrGlassPercent=0            ! 31
      IrWindowProt=0              ! 32
      IrExteriorDoors=0           ! 33
      IrBldFndConn=0              ! 34
      IrFoundation=0              ! 35
      IrAttachStruct=0            ! 37
      IrAppurtStruct=0            ! 38
      IrMechSystem=0              ! 39

	ivermajor=iversion/10
      rt_str='                    '
      ilen=LEN_TRIM(upx_str)

      istart=1
      do k=1,39
        do i=istart,ilen
          if (upx_str(i:i) .ne. ' ') goto 100
        end do
        return
 100    continue
        istart=i

        do i=istart,ilen
          if (upx_str(i:i) .eq. ',') then
            iend=i-1
            goto 200
	    else if (k .eq. 39 .and. i .eq. ilen) then
            iend=ilen
            goto 200
	    end if
        end do
        return
 200    continue
        temp_str=upx_str(istart:iend)

        if (k .eq. 1) then
          if (temp_str(1:2) .eq. '64') then
            ParseLocationDetailRecord=64
          else
            ParseLocationDetailRecord=0
          end if

        else if (k .eq. 2) then
          polid64=upx_str(istart:iend)

        else if (k .eq. 3) then
          locid64=upx_str(istart:iend)

        else if (k .eq. 5) then
          IrFloorOfInterest=StringToInteger(temp_str)
          if (IrFloorOfInterest .lt. 0 .or.
     &        IrFloorOfInterest .gt. 199) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 8) then
          IrTreeExposure=StringToInteger(temp_str)
          if (IrTreeExposure .lt. 0 .or. 
     &        IrTreeExposure .gt. 2) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 9) then
          IrSmallDebris=StringToInteger(temp_str)
          if (IrSmallDebris .lt. 0 .or.
     &        IrSmallDebris .gt. 2) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 10) then
          IrLargeDebris=StringToInteger(temp_str)
          if (IrLargeDebris .lt. 0 .or.
     &        IrLargeDebris .gt. 2) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 11) then
          IrTerrainRoughness=StringToInteger(temp_str)
          if (IrTerrainRoughness .lt. 0 .or.
     &        IrTerrainRoughness .gt. 4) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 12) then
          IrAdBldHeight=StringToInteger(temp_str)
          if (IrAdBldHeight .lt. 0 .or.
     &        IrAdBldHeight .gt. 199) then
            ParseLocationDetailRecord=-k
          end if

        elseif (k.eq.18) then
          IrFFE=StringToInteger(temp_str)     !***DRM***

        else if (k .eq. 20) then
          IrRoofGeometry=StringToInteger(temp_str)
          if (IrRoofGeometry .lt. 0 .or.
     &        IrRoofGeometry .gt. 10) then
            ParseLocationDetailRecord=-k
          end if
        
        else if (k .eq. 21) then
          IrRoofPitch=StringToInteger(temp_str)
          if (IrRoofPitch .lt. 0 .or.
     &        IrRoofPitch .gt. 3) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 22) then
          IrRoofCover=StringToInteger(temp_str)
          if (IrRoofCover .lt. 0 .or.
     &        IrRoofCover .gt. 15) then             ! ADDED: 12=FBC-Shingle, 13=FBC-Tile, 14=poured concrete, 15=Poor shingle
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 23) then
          IrRoofDeck=StringToInteger(temp_str)
          if (IrRoofDeck .lt. 0 .or.
     &        IrRoofDeck .gt. 8) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 24) then
          IrRoofCoverAttach=StringToInteger(temp_str)
          if (IrRoofCoverAttach .lt. 0 .or.
     &        IrRoofCoverAttach .gt. 4) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 25) then
          IrRoofDeckAttach=StringToInteger(temp_str)
          if (IrRoofDeckAttach .lt. 0 .or.
     &        IrRoofDeckAttach .gt. 7) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 26) then
          IrRoofAnchorage=StringToInteger(temp_str)
          if (IrRoofAnchorage .lt. 0 .or.
     &        IrRoofAnchorage .gt. 8) then            ! ADDED: 8=double wraps
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 27) then
          IrRoofBuilt=StringToInteger(temp_str)
          if (IrRoofBuilt .lt. 0 .or.
     &        IrRoofBuilt .gt. 2015) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 28) then
          IrWall=StringToInteger(temp_str)
          if (IrWall .lt. 0 .or.
     &        IrWall .gt. 9) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 29) then
          IrWallSiding=StringToInteger(temp_str)
          if (IrWallSiding .lt. 0 .or.
     &        IrWallSiding .gt. 7) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 30) then
          IrGlassType=StringToInteger(temp_str)
          if (IrGlassType .lt. 0 .or.
     &        IrGlassType .gt. 5) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 31) then
          IrGlassPercent=StringToInteger(temp_str)
          if (IrGlassPercent .lt. 0 .or.
     &        IrGlassPercent .gt. 4) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 32) then
          IrWindowProt=StringToInteger(temp_str)
          if (IrWindowProt .lt. 0 .or.
     &        IrWindowProt .gt. 6) then             ! ADDED: 4=basic, 5=plywood, 6=OSB
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 33) then
          IrExteriorDoors=StringToInteger(temp_str)
          if (IrExteriorDoors .lt. 0 .or.
     &        IrExteriorDoors .gt. 6) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 34) then
          IrBldFndConn=StringToInteger(temp_str)
          if (IrBldFndConn .lt. 0 .or.
     &        IrBldFndConn .gt. 6) then
            ParseLocationDetailRecord=-k
          end if
        
        elseif (k.eq.35) then                             ! ***DRM***
          IrFoundation=StringToInteger(temp_str)
          if (IrFoundation.lt.0.or.
     &        IrFoundation.gt.12) then
            ParseLocationDetailRecord=-k
          end if    
        
        else if (k .eq. 37) then
          IrAttachStruct=StringToInteger(temp_str)
          if (IrAttachStruct .lt. 0 .or.
     &        IrAttachStruct .gt. 8) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 38) then
          IrAppurtStruct=StringToInteger(temp_str)
          if (IrAppurtStruct .lt. 0 .or.
     &        IrAppurtStruct .gt. 7) then
            ParseLocationDetailRecord=-k
          end if

        else if (k .eq. 39) then
          IrMechSystem=StringToInteger(temp_str)
          if (IrMechSystem .lt. 0 .or.
     &        IrMechSystem .gt. 13) then
            ParseLocationDetailRecord=-k
          end if

        end if
        istart=iend+2
      end do

      return
      end

!
!******************************************************************************
!
      integer function StringToInteger(int_str)
!
!     converts a string of characters with values ranging from '0' to '9' to 
!     an integer. If, after trimming the string, any of the remaining characters 
!     are not between '0' and '9', the value returned will be -99999.
!
!******************************************************************************
!
      implicit none
      character*(*) int_str
      integer ndigits
      integer iachar
      integer i
      integer ivalue

      StringToInteger=0
      ndigits=LEN_TRIM(int_str)
      if (ndigits .gt. 9) then
	  ndigits=9
	end if

      do i=1,ndigits
        ivalue=iachar(int_str(i:i))-48
        if (ivalue .lt. 0 .or. ivalue .gt. 9) then
          StringToInteger=-99999
          return
        end if
        StringToInteger=StringToInteger+ivalue*10**(ndigits-i)
      end do
      
      return
      end
!
!******************************************************************************
!
      real function StringToReal(cstr)
!
!     converts a string of characters with values ranging from '0' to '9' to 
!     an integer. If, after trimming the string, any of the remaining characters 
!     are not between '0' and '9', the value returned will be -99999.
!
!******************************************************************************
!
      implicit none
      character*(*) cstr
      integer nchar
      integer idecimal
      integer nleft
      integer nright
      integer iachar
      integer i
      integer ivalue
      real rsign

      StringToReal=0
      nchar=LEN_TRIM(cstr)

      if (cstr(1:1) .eq. '-') then            ! strip off sign if negative
        cstr(1:nchar)=cstr(2:nchar)//' '
        nchar=LEN_TRIM(cstr)
        rsign=-1.
      else
        rsign=1.
      end if

      idecimal=nchar+1
      do i=1,nchar                            ! find decimal point, if applicable
        if (cstr(i:i) .eq. '.') then
          idecimal=i
        end if
      end do
 
      nleft=idecimal-1
      nright=nchar-nleft
      if (nright .ge. 1) then
        nright=nright-1
      end if

      do i=1,nleft                            ! compute value left of decimal
        ivalue=iachar(cstr(i:i))-48
        if (ivalue .lt. 0 .or. ivalue .gt. 9) then
          StringToReal=-99999.
          return
        end if
        StringToReal=StringToReal+real(ivalue)*10.0**(nleft-i)
      end do

      do i=nleft+2,nleft+1+nright             ! computer value right of decimal
        ivalue=iachar(cstr(i:i))-48
        if (ivalue .lt. 0 .or. ivalue .gt. 9) then
          StringToReal=-99999.
          return
        end if
        StringToReal=StringToReal+real(ivalue)*10.0**(nleft+1-i)
      end do
      StringToReal=StringToReal*rsign         ! change sign if negative
      
      return
	end
!
!******************************************************************************
!
      integer function ParsePerilCode(Peril)
!
!     returns a hurricane wind and hurricane storm surge peril code:
!       2=both hurricane wind and hurricane storm surge are covered perils
!       1=hurricane wind is a covered peril, but hurricane storm surge is not a covered peril
!       0=neither hurricane wind nor hurricane storm surge is a covered peril
!      -1=hurricane wind is not a covered peril, but hurricane storm surge is a covered peril
!
!******************************************************************************
!
      implicit none

      character*(*) Peril         ! peril code (up to 30 characters), codes are 3 characters, multiple perils must be separated by '+' characters
!
! local variables
!
	integer i
	integer istart
!
! initializations
!
      ParsePerilCode=0

	do i=1,30
		if (Peril(i:i) .ne. ' ') then		! skip leading spaces
			istart=i
			goto 100
		end if
	end do
	return
100	continue
	
	do i=istart,len(trim(Peril))-2,4
		if (Peril(i:i+2) .eq. 'PAL') then
			ParsePerilCode=2
			return
		else if (Peril(i:i+2) .eq. 'PWA' .or. 
     &           Peril(i:i+2) .eq. 'PWF' .or.
     &           Peril(i:i+2) .eq. 'PWH') then
			if (ParsePerilCode .eq. 0) then
				ParsePerilCode=1
			else if (ParsePerilCode .eq. -1) then		! handles these cases: PSH+PW*
				ParsePerilCode=2
				return
			end if
		else if (Peril(i:i+2) .eq. 'PSH') then
			if (ParsePerilCode .eq. 1) then					! handles these cases: PW*+PSH
				ParsePerilCode=2
				return
			else
				ParsePerilCode=-1
			end if
		end if
	end do

      return
	end
!
!******************************************************************************
!
      integer function ParseReStrings(TreatyName,Perils,NonLayeredLob,
     &																NonLayeredStates,LayeredLob)
!
!     parses reinsurance file fields that are strings
!
!******************************************************************************
!
      implicit none

	character*(*) TreatyName
	character*(*) Perils
	character*(*) NonLayeredLob
	character*(*) NonLayeredStates
	character*(*) LayeredLob
!
! local variables
!
      integer i

	ParseReStrings=0

	do i=32,1,-1 
		if (TreatyName(i:i) .eq. "!") then
			TreatyName=trim(TreatyName(1:i-1))
			goto 210
		end if
	end do
210	continue 
	
	do i=30,1,-1 
		if (Perils(i:i) .eq. "!") then
			Perils=trim(Perils(1:i-1))
			goto 220
		end if
	end do
220	continue 
	
	do i=256,1,-1 
		if (NonLayeredLob(i:i) .eq. "!") then
			NonLayeredLob=trim(NonLayeredLob(1:i-1))
			goto 230
		end if
	end do
230	continue 
	
	do i=256,1,-1 
		if (NonLayeredStates(i:i) .eq. "!") then
			NonLayeredStates=trim(NonLayeredStates(1:i-1))
			goto 240
		end if
	end do
240	continue 
	
	do i=256,1,-1 
		if (LayeredLob(i:i) .eq. "!") then
			LayeredLob=trim(LayeredLob(1:i-1))
			goto 250
		end if
	end do
250	continue 
	
	return
	end
	!end module ReadUnicedePX
