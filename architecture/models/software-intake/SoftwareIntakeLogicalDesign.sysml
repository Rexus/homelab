package Structure {
    doc /*
       Software intake admits accepted requests, forwards them and reuses disposable HTTP responses.
       Start from the native use cases and their scenarios; consumer verification and independent custody
       remain external responsibilities. Requirements are guardrails, not product choices. Logical
       structure, functions and use cases share native identities. Open the generated
       SoftwareIntakeLogicalDesign.svg and follow its Solution design or related views.
    */
    item def <'PAYLOAD'> Transfer;
    port def <'IF-transfer'> TransferPort { inout item payload : Transfer; }
    part def <'DEF-source'> ApprovedSource {
        doc /* Abstract role of an external repository service; an allowlist is a separate policy asset. */
        port access : TransferPort;
    }
    part def <'DEF-client'> UpdateClient {
        port access : TransferPort;
        doc /* Pull through the accepted route and verify publisher metadata/signatures locally. */
    }
    part def <'DEF-listener'> SharedListener {
        port inbound : TransferPort;
        port dispatch : TransferPort;
    }
    part def <'DEF-member'> ProxyMember {
        doc /* A software/virtual-resource member. Its guest storage does not identify a physical drive or host. */
        part <'DEF-member-proxy'> proxy : PolicyProxy;
        part <'DEF-member-cache'> storage : DisposableCache;
        dependency <'DEP-storage'> 'Uses local rebuildable storage' from proxy to storage;
    }

}

package Context {
    part <'L-context'> context {
        doc /* Interaction context. Tier and zone frames are explanatory view classifications,
               not deployed parts or composition owners. External sources/clients are reference roles. */
        part <'L-Proxy'> 'Policy proxy / HTTP cache' : PolicyProxy;
        part <'L-Cache'> 'Rebuildable cache storage' : DisposableCache {
            item <'L-cached-content'> 'Cached content' :>> DisposableCache::contents;
        }
        flow <'L-cache-io'> 'Disposable storage' from 'Policy proxy / HTTP cache'.cacheAccess.payload
            to 'Rebuildable cache storage'.access.payload;
        ref part <'L-Sources'> 'Approved external sources' : ApprovedSource {
            doc /* Abstract external repository role, not a component implemented by this system.
                   The permitted-source list is admission policy/configuration, not this participant. */
        }
        ref part <'L-Consumers'> 'Update Consumers' : UpdateClient {
            doc /* Separately owned external client roles; not a shared network or authority. */
            ref part <'L-Workloads'> 'Workload update clients' : UpdateClient;
            ref part <'L-Platform'> 'Platform update clients' : UpdateClient;
            ref part <'L-Control'> 'Infrastructure update clients' : UpdateClient;
        }
        flow <'L-upstream'> 'Source requests' from 'Policy proxy / HTTP cache'.outbound.payload
            to 'Approved external sources'.access.payload;
        flow <'L-request'> 'Proxy requests' from 'Update Consumers'.access.payload
            to 'Policy proxy / HTTP cache'.listener.payload;
    }
}

package FunctionalRequirements {
    requirement <'REQ-policy'> admittedSources {
        subject proxy : PolicyProxy;
        require constraint {
            doc /* The policy proxy shall deny external retrieval requests that fail the accepted client, destination or port policy. */
        }
    }
    satisfy requirement <'SAT-policy'> policySatisfied references admittedSources
        by context.'Policy proxy / HTTP cache' {
        doc /* Design assertion for the selected policy proxy; verification and site evidence are separate. */
    }
    dependency <'DEP-policy'> 'Admission obligation' from PolicyProxy to admittedSources;
}

package QualityRequirements {
    requirement <'REQ-integrity'> consumerVerification {
        doc SatisfactionReview /* The client role implements verify-before-use, supported by the shared
            APT/DNF package policy and client-side source TLS settings. This is a logical design assertion
            for clients honoring that policy; isolated APT evidence does not establish every client or site TLS. */
        subject client : UpdateClient;
        require constraint {
            doc /* The update client shall accept retrieved software for use only after the applicable source and publisher authenticity checks succeed, retaining end-to-end source TLS through CONNECT for HTTPS. */
        }
    }
    requirement <'REQ-custody'> independentRecovery {
        doc SatisfactionReview /* No satisfaction assertion: dedicated disposable cache storage is implemented,
            but the independently retained supply, isolation and recovery procedure are external and not fully
            modeled here. Cache separation alone does not establish recovery without the cache. */
        subject cache : DisposableCache;
        require constraint {
            doc /* The disposable cache shall keep the effects of losing its rebuildable data isolated from the independently retained recovery supply. */
        }
    }
    requirement <'REQ-egress'> noBypass {
        doc SatisfactionReview /* No satisfaction assertion: proxy routing and admission are implemented,
            but they do not prevent direct retrieval. Independent deployed firewall enforcement and its
            binding to these clients remain outside the modeled intake implementation. */
        subject client : UpdateClient;
        require constraint {
            doc /* The update client shall be unable to retrieve external software through a path that bypasses the independently enforced egress policy. */
        }
    }
    satisfy requirement <'SAT-integrity'> integritySatisfied references consumerVerification
        by context.'Update Consumers' {
        doc /* Client design claim, not a measured result. The shared package policy preserves signature,
               freshness and source TLS checks; external client/site configuration still needs verification. */
    }
    dependency <'DEP-integrity'> 'Verification obligation' from UpdateClient to consumerVerification;
    dependency <'DEP-custody'> 'Recovery separation' from DisposableCache to independentRecovery;
    dependency <'DEP-egress'> 'Network obligation' from UpdateClient to noBypass;
}

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

package Functions {
    action <'F-admit'> 'Check request access' {
        doc /* Check the accepted client, destination and port policy before content access. */
        in item request : Transfer;
        in attribute clientAllowed : ScalarValues::Boolean;
        in attribute destinationAllowed : ScalarValues::Boolean;
        in attribute portAllowed : ScalarValues::Boolean;
        out attribute admitted : ScalarValues::Boolean =
            AdmissionLogic::AdmissionAllowed(clientAllowed, destinationAllowed, portAllowed);
    }
    allocation <'ALLOC-F-admit-0'> allocate 'Check request access' to context.'Policy proxy / HTTP cache';
    dependency <'GUARD-F-admit'> from 'Check request access' to admittedSources;
    action <'F-http'> 'Fetch content from source' {
        doc /* Fetch or conditionally revalidate permitted repository content with its source. */
        in item request : Transfer;
        out item response : Transfer;
    }
    allocation <'ALLOC-F-http-0'> allocate 'Fetch content from source' to context.'Policy proxy / HTTP cache';
    dependency <'GUARD-F-http'> from 'Fetch content from source' to admittedSources;
    action <'F-cache'> 'Reuse fresh cached content' {
        doc /* Reuse only eligible fresh responses; respect privacy and freshness directives. Storage remains disposable. */
        in item response : Transfer;
        out item eligibleResponse : Transfer;
    }
    allocation <'ALLOC-F-cache-0'> allocate 'Reuse fresh cached content' to context.'Policy proxy / HTTP cache';
    allocation <'ALLOC-F-cache-1'> allocate 'Reuse fresh cached content' to context.'Rebuildable cache storage';
    dependency <'GUARD-F-cache'> from 'Reuse fresh cached content' to independentRecovery;
    action <'F-tunnel'> 'Forward HTTPS traffic' {
        doc /* Establish an admitted tunnel; preserve client-to-source TLS without inspecting or caching encrypted payload. */
        in item request : Transfer;
        out item response : Transfer;
    }
    allocation <'ALLOC-F-tunnel-0'> allocate 'Forward HTTPS traffic' to context.'Policy proxy / HTTP cache';
    dependency <'GUARD-F-tunnel'> from 'Forward HTTPS traffic' to consumerVerification;
    action <'F-verify'> 'Verify before use' {
        doc /* The external client verifies trusted publisher metadata and signatures; failure stops use. */
        in item response : Transfer;
        out attribute accepted : ScalarValues::Boolean;
    }
    allocation <'ALLOC-F-verify-0'> allocate 'Verify before use' to context.'Update Consumers';
    dependency <'GUARD-F-verify'> from 'Verify before use' to consumerVerification;
    dependency <'FUNCTION-H-request'> from 'Behavior'::'B-HTTP'::'H-request' to 'F-admit';
    dependency <'FUNCTION-H-check'> from 'Behavior'::'B-HTTP'::'H-check' to 'F-admit';
    dependency <'FUNCTION-H-denied'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-deny'::'H-denied' to 'F-admit';
    dependency <'FUNCTION-S-connect'> from 'Behavior'::'B-HTTPS'::'S-connect' to 'F-admit';
    dependency <'FUNCTION-S-check'> from 'Behavior'::'B-HTTPS'::'S-check' to 'F-admit';
    dependency <'FUNCTION-S-denied'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-deny'::'S-denied' to 'F-admit';
    dependency <'FUNCTION-H-fetch'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-fetch' to 'F-http';
    dependency <'FUNCTION-H-origin'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-origin' to 'F-http';
    dependency <'FUNCTION-H-response'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-response' to 'F-http';
    dependency <'FUNCTION-H-cached'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-hit'::'H-cached' to 'F-cache';
    dependency <'FUNCTION-H-cache-rules'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-cache-rules' to 'F-cache';
    dependency <'FUNCTION-S-open'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-allow'::'S-open' to 'F-tunnel';
    dependency <'FUNCTION-S-established'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-allow'::'S-established' to 'F-tunnel';
    dependency <'FUNCTION-S-ready'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-allow'::'S-ready' to 'F-tunnel';
    dependency <'FUNCTION-S-fetch'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-allow'::'S-fetch' to 'F-tunnel';
    dependency <'FUNCTION-S-response'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-allow'::'S-response' to 'F-tunnel';
    dependency <'FUNCTION-H-verify'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-verify' to 'F-verify';
    dependency <'FUNCTION-S-verify'> from 'Behavior'::'B-HTTPS'::'S-policy'::'S-allow'::'S-verify' to 'F-verify';
    dependency <'FUNCTION-H-lookup'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-lookup' to 'F-cache';
    dependency <'FUNCTION-H-source-failure'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-down'::'H-source-failure' to 'F-http';
    dependency <'FUNCTION-H-unavailable'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-down'::'H-unavailable' to 'F-http';
    dependency <'FUNCTION-H-accepted'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-integrity-choice'::'H-trust-ok'::'H-accepted' to 'F-verify';
    dependency <'FUNCTION-H-rejected'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-integrity-choice'::'H-trust-failed'::'H-rejected' to 'F-verify';
    dependency <'FUNCTION-H-stop'> from 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-no-content'::'H-stop' to 'F-verify';
}

package EngineeringViews {
    viewpoint def <'VP-engineering'> EngineeringRelationships {
        require constraint { doc /* Show which intent shapes the design, distinguish allocation from satisfaction and verification, and expose evidence gaps. */ }
    }
    view <'VIEW-engineering'> 'Engineering relationships' : StandardViewDefinitions::GeneralView {
        viewpoint : EngineeringRelationships;
        expose UseCases::'UC-update';
        expose FunctionalRequirements::admittedSources;
        expose FunctionalRequirements::policySatisfied;
        expose Functions::'F-admit';
        expose Functions::'F-http';
        expose Functions::'ALLOC-F-admit-0';
        expose Functions::'ALLOC-F-http-0';
        expose Context::context::'Policy proxy / HTTP cache';
        expose Verification::*;
        expose QualityRequirements::*;
        expose AdmissionAnalysis::*;
    }
}

package ExecutionTrace {
    dependency <'EXEC-refines'> 'Executable refinement' from RetrievalExecution::Retrieve to Behavior::HttpRetrieval;
    dependency <'EXEC-H-request'> from RetrievalExecution::Retrieve::'X-request' to 'Behavior'::'B-HTTP'::'H-request';
    dependency <'EXEC-H-check'> from RetrievalExecution::Retrieve::'X-check' to 'Behavior'::'B-HTTP'::'H-check';
    dependency <'EXEC-H-lookup'> from RetrievalExecution::Retrieve::'X-lookup' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-lookup';
    dependency <'EXEC-H-cached'> from RetrievalExecution::Retrieve::'X-cached' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-hit'::'H-cached';
    dependency <'EXEC-H-fetch'> from RetrievalExecution::Retrieve::'X-fetch' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-fetch';
    dependency <'EXEC-H-origin'> from RetrievalExecution::Retrieve::'X-origin' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-origin';
    dependency <'EXEC-H-cache-rules'> from RetrievalExecution::Retrieve::'X-cache-rules' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-cache-rules';
    dependency <'EXEC-H-response'> from RetrievalExecution::Retrieve::'X-response' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-ok'::'H-response';
    dependency <'EXEC-H-verify'> from RetrievalExecution::Retrieve::'X-verify' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-verify';
    dependency <'EXEC-H-accepted'> from RetrievalExecution::Retrieve::'X-accepted' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-integrity-choice'::'H-trust-ok'::'H-accepted';
    dependency <'EXEC-H-rejected'> from RetrievalExecution::Retrieve::'X-rejected' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-has-content'::'H-integrity-choice'::'H-trust-failed'::'H-rejected';
    dependency <'EXEC-H-denied'> from RetrievalExecution::Retrieve::'X-denied' to 'Behavior'::'B-HTTP'::'H-policy'::'H-deny'::'H-denied';
    dependency <'EXEC-H-source-failure'> from RetrievalExecution::Retrieve::'X-source-failure' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-down'::'H-source-failure';
    dependency <'EXEC-H-unavailable'> from RetrievalExecution::Retrieve::'X-unavailable' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-cache-choice'::'H-miss'::'H-source-choice'::'H-source-down'::'H-unavailable';
    dependency <'EXEC-H-stop'> from RetrievalExecution::Retrieve::'X-stop' to 'Behavior'::'B-HTTP'::'H-policy'::'H-allow'::'H-delivery-choice'::'H-no-content'::'H-stop';
    dependency <'EXEC-RUN-miss'> from RetrievalRuns::'RUN-miss' to UseCases::'UC-update'::'SC-http-miss';
    dependency <'EXEC-RUN-hit-offline'> from RetrievalRuns::'RUN-hit-offline' to UseCases::'UC-update'::'SC-http-hit';
    dependency <'EXEC-RUN-denied'> from RetrievalRuns::'RUN-denied' to UseCases::'UC-update'::'SC-http-denied';
    dependency <'EXEC-RUN-source-failure'> from RetrievalRuns::'RUN-source-failure' to UseCases::'UC-update'::'SC-http-source-failure';
    dependency <'EXEC-RUN-untrusted'> from RetrievalRuns::'RUN-untrusted' to UseCases::'UC-update'::'SC-http-untrusted';
    dependency <'EXEC-RUN-cache-untrusted'> from RetrievalRuns::'RUN-cache-untrusted' to UseCases::'UC-update'::'SC-http-cache-untrusted';
}
