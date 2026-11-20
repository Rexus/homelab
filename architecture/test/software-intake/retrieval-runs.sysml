package RetrievalRuns {
    action <'RUN-miss'> 'Retrieve from available source' : RetrievalExecution::Retrieve {
        in :>> clientAllowed = true;
        in :>> destinationAllowed = true;
        in :>> portAllowed = true;
        in :>> eligibleFreshResponse = false;
        in :>> sourceAvailable = true;
        in :>> contentVerified = true;
        doc Expected /* {"outcome": "accepted", "accepted": true, "cacheLookups": 1, "sourceRequests": 1, "verificationChecks": 1} */
    }
    action <'RUN-hit-offline'> 'Reuse fresh content while source is offline' : RetrievalExecution::Retrieve {
        in :>> clientAllowed = true;
        in :>> destinationAllowed = true;
        in :>> portAllowed = true;
        in :>> eligibleFreshResponse = true;
        in :>> sourceAvailable = false;
        in :>> contentVerified = true;
        doc Expected /* {"outcome": "accepted", "accepted": true, "cacheLookups": 1, "sourceRequests": 0, "verificationChecks": 1} */
    }
    action <'RUN-denied'> 'Deny even when content is cached' : RetrievalExecution::Retrieve {
        in :>> clientAllowed = true;
        in :>> destinationAllowed = false;
        in :>> portAllowed = true;
        in :>> eligibleFreshResponse = true;
        in :>> sourceAvailable = true;
        in :>> contentVerified = true;
        doc Expected /* {"outcome": "denied", "accepted": false, "cacheLookups": 0, "sourceRequests": 0, "verificationChecks": 0} */
    }
    action <'RUN-source-failure'> 'Stop after source failure' : RetrievalExecution::Retrieve {
        in :>> clientAllowed = true;
        in :>> destinationAllowed = true;
        in :>> portAllowed = true;
        in :>> eligibleFreshResponse = false;
        in :>> sourceAvailable = false;
        in :>> contentVerified = true;
        doc Expected /* {"outcome": "source-unavailable", "accepted": false, "cacheLookups": 1, "sourceRequests": 1, "verificationChecks": 0} */
    }
    action <'RUN-untrusted'> 'Reject untrusted source content' : RetrievalExecution::Retrieve {
        in :>> clientAllowed = true;
        in :>> destinationAllowed = true;
        in :>> portAllowed = true;
        in :>> eligibleFreshResponse = false;
        in :>> sourceAvailable = true;
        in :>> contentVerified = false;
        doc Expected /* {"outcome": "verification-failed", "accepted": false, "cacheLookups": 1, "sourceRequests": 1, "verificationChecks": 1} */
    }
    action <'RUN-cache-untrusted'> 'Reject untrusted cached content' : RetrievalExecution::Retrieve {
        in :>> clientAllowed = true;
        in :>> destinationAllowed = true;
        in :>> portAllowed = true;
        in :>> eligibleFreshResponse = true;
        in :>> sourceAvailable = false;
        in :>> contentVerified = false;
        doc Expected /* {"outcome": "verification-failed", "accepted": false, "cacheLookups": 1, "sourceRequests": 0, "verificationChecks": 1} */
    }
}
