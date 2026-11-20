package UseCases {
    use case def <'UC-update'> 'Retrieve and verify software' {
        subject <'UC-supply'> 'Controlled software supply' : PolicyProxy = context.'Policy proxy / HTTP cache';
        actor <'ACT-client'> 'Update client' : UpdateClient = context.'Update Consumers';
        actor <'ACT-source'> 'Approved source' : ApprovedSource = context.'Approved external sources';
        objective { doc /* Receive permitted content through accepted supply or an explicit denial.
            The external client retains responsibility for publisher verification before use. */
            require admittedSources;
        }
        // Reference actions describe alternative scenarios, not concurrent performances.
        ref action <'SC-http-miss'> 'Retrieve or revalidate HTTP content' : Behavior::HttpRetrieval {
            doc Trigger /* An update client requests HTTP repository content. */
            doc Preconditions /* The route and trust policy are configured; content is absent or needs revalidation. */
            doc Outcome /* Receive an allowed response, then verify trusted metadata and signatures locally. Verification failure stops use; it never approves an artifact. */
            attribute :>> admitted = true;
            attribute :>> eligibleFreshResponse = false;
            attribute :>> sourceAvailable = true;
            attribute :>> responseDelivered = true;
            attribute :>> contentVerified = true;
        }
        ref action <'SC-http-hit'> 'Reuse a fresh HTTP response' : Behavior::HttpRetrieval {
            doc Trigger /* An update client repeats an eligible HTTP request. */
            doc Preconditions /* Policy admits the request and an eligible fresh cached response exists. */
            doc Outcome /* Receive cached content without an origin fetch, then perform the same local verification as a miss. */
            attribute :>> admitted = true;
            attribute :>> eligibleFreshResponse = true;
            attribute :>> responseDelivered = true;
            attribute :>> contentVerified = true;
        }
        ref action <'SC-http-denied'> 'Reject a disallowed HTTP request' : Behavior::HttpRetrieval {
            doc Trigger /* A client requests a disallowed HTTP destination, port or route. */
            doc Preconditions /* At least one admission condition fails. */
            doc Outcome /* Receive denial without a cache lookup or source fetch. */
            attribute :>> admitted = false;
        }
        ref action <'SC-http-source-failure'> 'Stop when the source is unavailable' : Behavior::HttpRetrieval {
            doc Trigger /* An update client requests HTTP repository content. */
            doc Preconditions /* An admitted request has no eligible fresh response and its source attempt fails. */
            doc Outcome /* Return a retrieval error and stop without content verification. */
            attribute :>> admitted = true;
            attribute :>> eligibleFreshResponse = false;
            attribute :>> sourceAvailable = false;
            attribute :>> responseDelivered = false;
        }
        ref action <'SC-http-untrusted'> 'Reject untrusted source content' : Behavior::HttpRetrieval {
            doc Trigger /* An update client requests HTTP repository content. */
            doc Preconditions /* An admitted source retrieval completes but publisher verification fails. */
            doc Outcome /* Reject received content before use. */
            attribute :>> admitted = true;
            attribute :>> eligibleFreshResponse = false;
            attribute :>> sourceAvailable = true;
            attribute :>> responseDelivered = true;
            attribute :>> contentVerified = false;
        }
        ref action <'SC-http-cache-untrusted'> 'Reject untrusted cached content' : Behavior::HttpRetrieval {
            doc Trigger /* An update client requests HTTP repository content. */
            doc Preconditions /* A fresh eligible cached response is returned but publisher verification fails. */
            doc Outcome /* Reject cached content before use; a cache hit does not imply trust. */
            attribute :>> admitted = true;
            attribute :>> eligibleFreshResponse = true;
            attribute :>> responseDelivered = true;
            attribute :>> contentVerified = false;
        }
        ref action <'SC-https'> 'Retrieve through source TLS' : Behavior::HttpsRetrieval {
            doc Trigger /* An update client requests an HTTPS repository through CONNECT. */
            doc Preconditions /* Admission succeeds; TCP and source-authenticated TLS can be established. */
            doc Outcome /* Receive content through the tunnel and verify it at the client. No TLS interception, payload caching or scanning. Transport or verification failure stops retrieval; detailed transport error exchanges are outside this sequence. */
            attribute :>> admitted = true;
        }
        ref action <'SC-https-denied'> 'Reject a disallowed CONNECT request' : Behavior::HttpsRetrieval {
            doc Trigger /* A client attempts a disallowed CONNECT request. */
            doc Preconditions /* At least one admission condition fails. */
            doc Outcome /* Receive denial without a connection to the source. */
            attribute :>> admitted = false;
        }
    }
    dependency <'DEP-usecase'> 'Uses controlled acquisition' from 'Retrieve and verify software' to context;
}
