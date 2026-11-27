package AdmissionLogic {
    calc def <'CALC-admission'> AdmissionAllowed {
        in clientAllowed : ScalarValues::Boolean;
        in destinationAllowed : ScalarValues::Boolean;
        in portAllowed : ScalarValues::Boolean;
        return admitted : ScalarValues::Boolean = clientAllowed and destinationAllowed and portAllowed;
    }
}

package RetrievalExecution {
    private import ScalarValues::*;
    action def <'X-HTTP'> Retrieve {
        doc /* Executable HTTP refinement: one request, eligible fresh-cache reuse, one source attempt,
               and client verification. Availability and trust are supplied environment outcomes.
               No packet timing, retry, stale-if-error fallback, TLS or cryptographic execution. */
        in clientAllowed : Boolean;
        in destinationAllowed : Boolean;
        in portAllowed : Boolean;
        in eligibleFreshResponse : Boolean;
        in sourceAvailable : Boolean;
        in contentVerified : Boolean;
        out accepted : Boolean := false;
        out outcome : String := "pending";
        out cacheLookups : Integer := 0;
        out sourceRequests : Integer := 0;
        out verificationChecks : Integer := 0;
        attribute admitted : Boolean := false;
        attribute delivered : Boolean := false;

        first start;
        then action <'X-request'> request;
        then action <'X-check'> admission assign admitted :=
            AdmissionLogic::AdmissionAllowed(clientAllowed, destinationAllowed, portAllowed);
        then decide <'XD-policy'> policy;
            if admitted then lookup;
            else deny;
        action <'X-lookup'> lookup assign cacheLookups := cacheLookups + 1;
        then decide <'XD-cache'> cache;
            if eligibleFreshResponse then cached;
            else fetch;
        action <'X-cached'> cached assign delivered := true;
        then contentReady;
        action <'X-fetch'> fetch assign sourceRequests := sourceRequests + 1;
        then decide <'XD-source'> source;
            if sourceAvailable then origin;
            else sourceFailure;
        action <'X-origin'> origin assign delivered := true;
        then action <'X-cache-rules'> cacheRules;
        then action <'X-response'> response;
        then contentReady;
        merge <'XM-content'> contentReady;
        then action <'X-verify'> verifyContent {
            first start;
            then assign verificationChecks := verificationChecks + 1;
            then assign accepted := delivered and contentVerified;
            then done;
        }
        then decide <'XD-integrity'> integrity;
            if accepted then complete;
            else rejectContent;
        action <'X-accepted'> complete assign outcome := "accepted";
        then finishRetrieval;
        action <'X-rejected'> rejectContent assign outcome := "verification-failed";
        then finishRetrieval;
        action <'X-denied'> deny assign outcome := "denied";
        then finishRetrieval;
        action <'X-source-failure'> sourceFailure;
        then action <'X-unavailable'> unavailable assign outcome := "source-unavailable";
        then action <'X-stop'> stopWithoutContent;
        then finishRetrieval;
        merge <'XM-finish'> finishRetrieval;
        then done;
    }
}

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
