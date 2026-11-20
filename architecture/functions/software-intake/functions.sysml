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
