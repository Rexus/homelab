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
