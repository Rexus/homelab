package Behavior {
    abstract flow def <'MSG-request'> RequestMessage;
    abstract flow def <'MSG-response'> ResponseMessage;
    abstract flow def <'MSG-process'> ProcessingStep;

    action def <'B-HTTP'> HttpRetrieval {
        doc /* Expected HTTP behavior, including admission, cache freshness, source failure and client verification alternatives.
               Guards are observed outcomes, not predictions made by this model. */
        attribute <'H-admitted'> admitted : ScalarValues::Boolean;
        attribute <'H-fresh'> eligibleFreshResponse : ScalarValues::Boolean;
        attribute <'H-source-available'> sourceAvailable : ScalarValues::Boolean;
        attribute <'H-delivered'> responseDelivered : ScalarValues::Boolean;
        attribute <'H-trusted'> contentVerified : ScalarValues::Boolean;
        ref part <'H-client'> 'Update client' : UpdateClient {
            event occurrence requestSent; event occurrence responseReceived;
            event occurrence verifyStarted; event occurrence verifyCompleted;
            event occurrence accepted; event occurrence rejected; event occurrence stopped;
        }
        ref part <'H-proxy'> 'Policy proxy' : PolicyProxy {
            event occurrence requestReceived; event occurrence checkStarted; event occurrence checkCompleted;
            event occurrence denied; event occurrence cachedResponseSent; event occurrence fetchSent;
            event occurrence originReceived; event occurrence rulesStarted; event occurrence rulesCompleted;
            event occurrence responseSent; event occurrence lookupStarted; event occurrence lookupCompleted;
            event occurrence failureObserved; event occurrence failureProcessed; event occurrence errorSent;
        }
        ref part <'H-source'> 'Approved source' : ApprovedSource {
            event occurrence fetchReceived; event occurrence responseSent;
        }
        bind 'Update client' = context.'Update Consumers';
        bind 'Policy proxy' = context.'Policy proxy / HTTP cache';
        bind 'Approved source' = context.'Approved external sources';

        message <'H-request'> 'HTTP repository request' : RequestMessage
            from 'Update client'.requestSent to 'Policy proxy'.requestReceived;
        then message <'H-check'> 'Check client, destination and port' : ProcessingStep
            from 'Policy proxy'.checkStarted to 'Policy proxy'.checkCompleted;
        then action <'H-policy'> admission if admitted
        action <'H-allow'> 'Allowed' {
            message <'H-lookup'> 'Look up eligible fresh content' : ProcessingStep
                from 'Policy proxy'.lookupStarted to 'Policy proxy'.lookupCompleted;
            then action <'H-cache-choice'> freshness if eligibleFreshResponse
            action <'H-hit'> 'Fresh eligible cache hit' {
                message <'H-cached'> 'Return cached response' : ResponseMessage
                    from 'Policy proxy'.cachedResponseSent to 'Update client'.responseReceived;
            } else action <'H-miss'> 'Absent or requires revalidation' {
                message <'H-fetch'> 'Fetch or conditionally revalidate' : RequestMessage
                    from 'Policy proxy'.fetchSent to 'Approved source'.fetchReceived;
                then action <'H-source-choice'> availability if sourceAvailable
                action <'H-source-ok'> 'Source available' {
                    message <'H-origin'> 'Content or freshness response' : ResponseMessage
                        from 'Approved source'.responseSent to 'Policy proxy'.originReceived;
                    then message <'H-cache-rules'> 'Apply cache and privacy rules' : ProcessingStep
                        from 'Policy proxy'.rulesStarted to 'Policy proxy'.rulesCompleted;
                    then message <'H-response'> 'Return response' : ResponseMessage
                        from 'Policy proxy'.responseSent to 'Update client'.responseReceived;
                } else action <'H-source-down'> 'Source unavailable' {
                    message <'H-source-failure'> 'Observe source failure' : ProcessingStep
                        from 'Policy proxy'.failureObserved to 'Policy proxy'.failureProcessed;
                    then message <'H-unavailable'> 'Return retrieval error without content' : ResponseMessage
                        from 'Policy proxy'.errorSent to 'Update client'.responseReceived;
                }
            }
            then action <'H-delivery-choice'> delivery if responseDelivered
            action <'H-has-content'> 'Content received' {
                message <'H-verify'> 'Verify trusted metadata / signatures' : ProcessingStep
                    from 'Update client'.verifyStarted to 'Update client'.verifyCompleted;
                then action <'H-integrity-choice'> integrity if contentVerified
                action <'H-trust-ok'> 'Verification passed' {
                    message <'H-accepted'> 'Accept verified content for use' : ProcessingStep
                        from 'Update client'.verifyCompleted to 'Update client'.accepted;
                } else action <'H-trust-failed'> 'Verification failed' {
                    message <'H-rejected'> 'Reject content; stop before use' : ProcessingStep
                        from 'Update client'.verifyCompleted to 'Update client'.rejected;
                }
            } else action <'H-no-content'> 'No content received' {
                message <'H-stop'> 'Stop retrieval without verifying content' : ProcessingStep
                    from 'Update client'.responseReceived to 'Update client'.stopped;
            }
        } else action <'H-deny'> 'Denied by policy' {
            message <'H-denied'> 'Deny without a cache lookup or source fetch' : ResponseMessage
                from 'Policy proxy'.denied to 'Update client'.responseReceived;
        }
    }

    action def <'B-HTTPS'> HttpsRetrieval {
        doc /* Expected successful CONNECT/TLS exchange or admission denial. TCP/TLS failures stop
               retrieval; retries and detailed transport error exchanges are outside this view.
               Client-to-source messages pass through the established tunnel. No payload cache or scanning. */
        attribute <'S-admitted'> admitted : ScalarValues::Boolean;
        ref part <'S-client'> 'Update client' : UpdateClient {
            event occurrence connectSent; event occurrence connectReceived;
            event occurrence requestSent; event occurrence responseReceived;
            event occurrence verifyStarted; event occurrence verifyCompleted;
        }
        ref part <'S-proxy'> 'Policy proxy' : PolicyProxy {
            event occurrence connectReceived; event occurrence checkStarted; event occurrence checkCompleted;
            event occurrence denied; event occurrence openSent; event occurrence established;
            event occurrence readySent;
        }
        ref part <'S-source'> 'Approved source' : ApprovedSource {
            event occurrence openReceived; event occurrence established;
            event occurrence requestReceived; event occurrence responseSent;
        }
        bind 'Update client' = context.'Update Consumers';
        bind 'Policy proxy' = context.'Policy proxy / HTTP cache';
        bind 'Approved source' = context.'Approved external sources';

        message <'S-connect'> 'CONNECT source:443' : RequestMessage
            from 'Update client'.connectSent to 'Policy proxy'.connectReceived;
        then message <'S-check'> 'Check client, destination and port' : ProcessingStep
            from 'Policy proxy'.checkStarted to 'Policy proxy'.checkCompleted;
        then action <'S-policy'> admission if admitted
        action <'S-allow'> 'Allowed; TCP/TLS succeeds' {
            message <'S-open'> 'Open permitted TCP connection' : RequestMessage
                from 'Policy proxy'.openSent to 'Approved source'.openReceived;
            then message <'S-established'> 'Connection established' : ResponseMessage
                from 'Approved source'.established to 'Policy proxy'.established;
            then message <'S-ready'> '200 Connection Established' : ResponseMessage
                from 'Policy proxy'.readySent to 'Update client'.connectReceived;
            then message <'S-fetch'> 'Fetch through client-to-source TLS' : RequestMessage
                from 'Update client'.requestSent to 'Approved source'.requestReceived {
                doc /* Client authenticates source TLS through the tunnel. No payload caching or scanning. */
            }
            then message <'S-response'> 'Encrypted response through the tunnel' : ResponseMessage
                from 'Approved source'.responseSent to 'Update client'.responseReceived;
            then message <'S-verify'> 'Verify trusted metadata / signatures; stop on failure' : ProcessingStep
                from 'Update client'.verifyStarted to 'Update client'.verifyCompleted;
        } else action <'S-deny'> 'Denied by policy' {
            message <'S-denied'> 'Deny without a source connection' : ResponseMessage
                from 'Policy proxy'.denied to 'Update client'.connectReceived;
        }
    }
    dependency <'DEP-http-usecase'> from HttpRetrieval to 'Retrieve and verify software';
    dependency <'DEP-https-usecase'> from HttpsRetrieval to 'Retrieve and verify software';
    dependency <'DEP-http-policy'> from HttpRetrieval to admittedSources;
    dependency <'DEP-https-policy'> from HttpsRetrieval to admittedSources;
    dependency <'DEP-http-integrity'> from HttpRetrieval to consumerVerification;
    dependency <'DEP-https-integrity'> from HttpsRetrieval to consumerVerification;
}

package AdmissionAnalysis {
    private import AdmissionLogic::*;
    calc def <'CALC-shortcut'> CacheShortcut {
        doc /* Rejected candidate: a warm cache must not bypass admission. An analysis alternative, not an implementation. */
        in clientAllowed : ScalarValues::Boolean;
        in destinationAllowed : ScalarValues::Boolean;
        in portAllowed : ScalarValues::Boolean;
        in cacheHit : ScalarValues::Boolean;
        return admitted : ScalarValues::Boolean = cacheHit or AdmissionAllowed(clientAllowed, destinationAllowed, portAllowed);
    }
    analysis def <'AN-admission'> AdmissionOrderReview {
        subject proxy : PolicyProxy;
        objective { doc /* Find whether a proposed cache shortcut admits requests rejected by the policy predicate. */ }
        in clientAllowed : ScalarValues::Boolean;
        in destinationAllowed : ScalarValues::Boolean;
        in portAllowed : ScalarValues::Boolean;
        in cacheHit : ScalarValues::Boolean;
        return counterexample : ScalarValues::Boolean =
            CacheShortcut(clientAllowed, destinationAllowed, portAllowed, cacheHit) and
            not AdmissionAllowed(clientAllowed, destinationAllowed, portAllowed);
    }
    dependency <'AN-policy'> 'Evaluates admission obligation' from AdmissionOrderReview to admittedSources;
    dependency <'AN-function'> 'Evaluates admission function' from AdmissionOrderReview to Functions::'F-admit';
}
