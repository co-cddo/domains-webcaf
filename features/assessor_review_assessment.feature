Feature: Independent assurance reviewer reviews a submitted self-assessment

  Background:
    Given Organisation "Ministry of Agriculture" of type "ministerial-department" exists with systems "System 1, System 2, System 3"
    And the user "alice@example.gov.uk" exists
    And User "alice@example.gov.uk" has the profile "GovAssure lead" assigned in "Ministry of Agriculture"
    And the user "assessor_1@example.com" exists
    And User "assessor_1@example.com" has the profile "Independent assurance reviewer" assigned in "Ministry of Agriculture"
    And the application is running
    And cookies have been "accepted"
    And there is a "enhanced" profile assessment for "System 1", "Ministry of Agriculture", for the period "current" in "draft" status and data "alice_completed_assessment.json"

    Then the user logs in with username "alice@example.gov.uk" and password "password"
    And click link with text "View 1 draft self-assessment"
    And click link in table row containing value "System 1" with text "View"
    Then page has heading "Complete a WebCAF self-assessment"
    And get assessment id from url and add to context
    And confirm the current assessment has expected data "alice_completed_assessment.json"
    And confirm the current assessment has version as "caf40" type as "independent" and profile as "enhanced"
    And click link with text "Complete the full self-assessment"
    When click button with text "Save and Send for Review"
    Then page has heading "Self-assessment completed"
    And logs out by clicking link

  Scenario: Independent assessor reviews a submitted self-assessment
    Given the application is running
    When the user logs in with username "assessor_1@example.com" and password "password"
    And page has heading "Ministry of Agriculture self-assessments"
    And click link in table row containing value "System 1" with text "Review"
    And page has heading "Review a WebCAF self-assessment"
    And store the current review id from url and add to context
    And click link with text "Confirm system overview"
    And confirm the current review has expected data
    And click button with text "Save and continue"
    And click link with text "Objective A: Managing security risk"
    And Fill review outcome "A1.a Board direction" with "achieved, partially-achieved, not-achieved" with "all,all,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A1.b Roles and responsibilities" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A1.c Decision-making" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A2.a Risk management process" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A2.b Understanding threat" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A2.c Assurance" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A3.a Asset management" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A4.a Supply chain" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "A4.b Secure software development and support" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Add Areas of good practice
    And Add Areas for improvement
    Then click button with text "Save and continue"

#    Automatically taken to next objective after the final CO is done, so no need to click the next objective link
    And Fill review outcome "B1.a Policy, process and procedure development" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B1.b Policy, process and procedure implementation" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B2.a Identity verification, authentication and authorisation" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B2.b Device management" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B2.c Privileged user management" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B2.d Identity and access management (idam)" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B3.a Understanding data" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B3.b Data in transit" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B3.c Stored data" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B3.d Mobile data" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B3.e Media / equipment sanitisation" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B4.a Secure by design" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B4.b Secure configuration" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B4.c Secure management" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B4.d Vulnerability management" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B5.a Resilience preparation" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B5.b Design for resilience" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B5.c Backups" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B6.a Cyber security culture" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "B6.b Cyber security training" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Add Areas of good practice
    And Add Areas for improvement
    Then click button with text "Save and continue"

    #    Automatically taken to next objective after the final CO is done, so no need to click the next objective link
    And Fill review outcome "C1.a Sources and tools for logging and monitoring" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "C1.b Securing logs" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "C1.c Generating alerts" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "C1.d Triage of security alerts" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "C1.e Personnel skills for monitoring and detection" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "C1.f Understanding user's and system's behaviour, and threat intelligence" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "C2.a Threat hunting" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Add Areas of good practice
    And Add Areas for improvement
    Then click button with text "Save and continue"

    #    Automatically taken to next objective after the final CO is done, so no need to click the next objective link
    And Fill review outcome "D1.a Response plan" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "D1.b Response and recovery capability" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "D1.c Testing and exercising" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "D2.a Post incident analysis" with "achieved, partially-achieved, not-achieved" with "all,none,none"
    And Fill review outcome confirm status "Achieved" with "Independent review answer"
    And Fill review outcome "D2.b Using incidents to drive improvements" with "achieved, partially-achieved, not-achieved" with "none,none,none"
    And Fill review outcome confirm status "Not achieved" with "Independent review answer"
    And Add Areas of good practice
    And Add Areas for improvement
    Then click button with text "Back to review draft review"

    And add review recommendation for "D2.b Using incidents to drive improvements" with "Recommendation for improvement D2.b"
    And add review recommendation for "A1.a Board Direction" with "Recommendation for improvement A1.a"
    Then Navigate back to the review summary page

#    Add the additional details needed for the review to be submitted
    And Enter IAR period
    And Add company details
    And Add review method
    And Add quality of self assessment
    Then click link with text "Create report"
    Then click button with text "Save and continue"
    Then click button with text "View report"
    Then page has heading "GovAssure Independent Assurance Review Report (IARR)"
    And page contains text "This report is UK OFFICIAL-SENSITIVE." in banner

    Then Navigate to review history page
    And page has heading "Report history"
    And click link with text "Mark latest report version as final"
    Then page has heading "Do you want version 1 to be the final report?"
    And click button with text "Confirm and make final"
    And confirm review data has expected data "assessor_finalised_review.json"
