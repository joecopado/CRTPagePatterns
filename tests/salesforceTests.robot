# NOTE: readme.txt contains important information you need to take into account
# before running this suite.

*** Settings ***
Resource                      ../resources/common.robot
Suite Setup                   Setup Browser
Suite Teardown                End suite


*** Variables ***


*** Test Cases ***
Entering A Lead
#Dev1 - SDO
    ${token}=    JwtAuthenticate    ${client_iddev1}    ${usernamedev1}    ${private_keydev1}    sandbox=true
    JwtLogin

#Slockard
    ${token}=    JwtAuthenticate    ${client_idSlock}    ${usernameSlock}    ${private_keySlock}    
    JwtLogin

#SECICD
    ${token}=    JwtAuthenticate    ${client_idCICD}    ${usernameCICD}    ${private_keyCICD}    
    JwtLogin







