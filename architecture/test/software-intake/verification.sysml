package Verification {
    // Verification intent, not recorded pass verdicts. External test runners supply evidence.
    verification def <'VC-http-miss'> 'Assess admitted HTTP retrieval' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* An admitted miss or stale response reaches the source; cache/privacy rules are respected and the client verifies before use. Unsigned or expired metadata is rejected unless an explicit trusted-source exception was selected. */
    }
    dependency <'COVER-SC-http-miss'> from 'VC-http-miss' to UseCases::'UC-update'::'SC-http-miss';
    verification def <'VC-http-hit'> 'Assess admitted cache reuse' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* A repeated eligible fresh response is served without another origin request. The client still verifies trusted metadata/signatures. */
    }
    dependency <'COVER-SC-http-hit'> from 'VC-http-hit' to UseCases::'UC-update'::'SC-http-hit';
    verification def <'VC-http-denied'> 'Assess HTTP admission denial' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* A rejected client, destination or port receives denial and the recording source sees no request. */
    }
    dependency <'COVER-SC-http-denied'> from 'VC-http-denied' to UseCases::'UC-update'::'SC-http-denied';
    verification def <'VC-https'> 'Assess CONNECT admission' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* An admitted CONNECT establishes source-authenticated client TLS. Encrypted payload is neither cached nor inspected; client verification still applies. */
        doc Manual /* Run the Stage 1 accepted-source HTTPS retrieval on the deployed route; verify source certificate/hostname, payload integrity and refusal of invalid trust. The isolated HTTP fixture does not forward CONNECT. */
    }
    dependency <'COVER-SC-https'> from 'VC-https' to UseCases::'UC-update'::'SC-https';
    verification def <'VC-https-denied'> 'Assess CONNECT denial' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* A disallowed CONNECT destination, client or port receives denial without opening a source connection. */
    }
    dependency <'COVER-SC-https-denied'> from 'VC-https-denied' to UseCases::'UC-update'::'SC-https-denied';
    verification def <'VC-integrity'> 'Assess source and publisher trust' {
        subject client : UpdateClient;
        objective { verify consumerVerification; }
        doc Acceptance /* Client authenticates the source TLS endpoint and rejects untrusted publisher metadata before use; test the selected trust exceptions explicitly. Successful CONNECT/TLS still needs site evidence. */
    }
    verification def <'VC-custody'> 'Demonstrate independent recovery' {
        subject cache : DisposableCache;
        objective { verify independentRecovery; }
        doc Acceptance /* Remove disposable cache data and demonstrate recovery from independently retained supply. This is a site recovery demonstration, not inferred from storage configuration. */
    }
    verification def <'VC-egress'> 'Demonstrate bypass prevention' {
        subject client : UpdateClient;
        objective { verify noBypass; }
        doc Acceptance /* Attempt direct external access bypassing the accepted route and show independent network enforcement rejects it. This requires the site network policy and deployed-route evidence. */
    }
    verification def <'VC-http-source-failure'> 'Return a retrieval error on source failure' {
        subject target : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* A source failure after an admitted miss produces no usable content, no client verification and no implicit stale fallback. The execution model supplies availability; deployed failure behavior needs separate evidence. */
    }
    dependency <'COVER-SC-http-source-failure'> from 'VC-http-source-failure' to UseCases::'UC-update'::'SC-http-source-failure';
    verification def <'VC-http-untrusted'> 'Reject untrusted retrieved content' {
        subject target : UpdateClient;
        objective { verify consumerVerification; }
        doc Acceptance /* When publisher verification fails after retrieval, the client rejects the content before use. Model trust is an input, not a cryptographic check. */
    }
    dependency <'COVER-SC-http-untrusted'> from 'VC-http-untrusted' to UseCases::'UC-update'::'SC-http-untrusted';
    verification def <'VC-http-cache-untrusted'> 'Reject untrusted cached content' {
        subject target : UpdateClient;
        objective { verify consumerVerification; }
        doc Acceptance /* Cached content is verified at the client and rejected when trust fails, without a source fetch. Model trust is an input, not a cryptographic check. */
    }
    dependency <'COVER-SC-http-cache-untrusted'> from 'VC-http-cache-untrusted' to UseCases::'UC-update'::'SC-http-cache-untrusted';
}
