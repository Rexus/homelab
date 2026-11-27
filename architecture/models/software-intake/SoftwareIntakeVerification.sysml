package Verification {
    // Verification intent, not recorded pass verdicts. External test runners supply evidence.
    verification def <'VC-http-miss'> 'Assess admitted HTTP retrieval' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* Both variants contact the source. Received content follows the configured cache/privacy policy and passes client verification before use; unsigned or expired metadata is rejected unless explicitly excepted. */
        doc Method /* Test */
        doc Setup /* Admitted client and source; empty or expired HTTP cache; configured publisher trust. */
        doc Action /* Request repository content once with an empty cache and once with an expired entry. */
    }
    dependency <'COVER-SC-http-miss'> from 'VC-http-miss' to UseCases::'UC-update'::'SC-http-miss';
    verification def <'VC-http-hit'> 'Assess admitted cache reuse' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* No additional source request occurs. The client verifies the returned content before accepting it. */
        doc Method /* Test */
        doc Setup /* Admitted request; eligible fresh cached content; trusted publisher metadata. */
        doc Action /* Repeat the request while counting requests at the source and verification at the client. */
    }
    dependency <'COVER-SC-http-hit'> from 'VC-http-hit' to UseCases::'UC-update'::'SC-http-hit';
    verification def <'VC-http-denied'> 'Assess HTTP admission denial' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* Each request is denied. The source records zero requests; cached content is not returned. */
        doc Method /* Test */
        doc Setup /* Recording source; change one of the permitted client, destination or port conditions at a time. */
        doc Action /* Issue an HTTP request for each disallowed condition, including a previously cached URL. */
    }
    dependency <'COVER-SC-http-denied'> from 'VC-http-denied' to UseCases::'UC-update'::'SC-http-denied';
    verification def <'VC-https'> 'Assess CONNECT admission' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* Client TLS authenticates the source certificate and hostname end to end. The proxy neither inspects nor caches decrypted payload; client content verification succeeds before use. */
        doc Method /* Test */
        doc Setup /* Deployed accepted route; trusted HTTPS source; source and proxy observations available. */
        doc Action /* Establish CONNECT and retrieve content; inspect client TLS validation and proxy cache/log evidence. */
        doc Manual /* Run the Stage 1 accepted-source HTTPS retrieval on the deployed route; verify source certificate/hostname, payload integrity and refusal of invalid trust. The isolated HTTP fixture does not forward CONNECT. */
    }
    dependency <'COVER-SC-https'> from 'VC-https' to UseCases::'UC-update'::'SC-https';
    verification def <'VC-https-denied'> 'Assess CONNECT denial' {
        subject proxy : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* CONNECT is denied and the source records zero connections. */
        doc Method /* Test */
        doc Setup /* Recording source; a disallowed CONNECT destination, client or port. */
        doc Action /* Attempt CONNECT for each disallowed condition. */
    }
    dependency <'COVER-SC-https-denied'> from 'VC-https-denied' to UseCases::'UC-update'::'SC-https-denied';
    verification def <'VC-integrity'> 'Assess source and publisher trust' {
        subject client : UpdateClient;
        objective { verify consumerVerification; }
        doc Acceptance /* Valid content passes its configured checks. Each invalid case is rejected before use unless that exact exception is explicitly authorized by the declared trust policy. */
        doc Method /* Test */
        doc Setup /* Declared source/publisher trust policy, including any explicitly accepted exceptions. */
        doc Action /* Retrieve valid content, then repeat with an untrusted TLS peer, wrong hostname and untrusted publisher metadata. */
    }
    verification def <'VC-custody'> 'Demonstrate independent recovery' {
        subject cache : DisposableCache;
        objective { verify independentRecovery; }
        doc Acceptance /* The independently retained supply is unchanged and the defined recovery procedure succeeds without the deleted cache data. */
        doc Method /* Demonstration */
        doc Setup /* Disposable test cache and independently retained recovery supply with recorded contents. */
        doc Action /* Remove the disposable cache data, then perform recovery using the retained supply. */
    }
    verification def <'VC-egress'> 'Demonstrate bypass prevention' {
        subject client : UpdateClient;
        objective { verify noBypass; }
        doc Acceptance /* Independent network enforcement rejects the bypass attempt and no software is retrieved through it. */
        doc Method /* Test */
        doc Setup /* Deployed client, accepted egress route, independent network policy and a recording external source. */
        doc Action /* Attempt direct external retrieval while bypassing the accepted route. */
    }
    verification def <'VC-http-source-failure'> 'Return a retrieval error on source failure' {
        subject target : PolicyProxy;
        objective { verify admittedSources; }
        doc Acceptance /* Retrieval reports failure, delivers no usable content, performs zero content-verification checks and does not serve a stale fallback. */
        doc Method /* Test */
        doc Setup /* Admitted uncached request; source configured to return an error or refuse the connection. */
        doc Action /* Request the object for each source-failure condition. */
    }
    dependency <'COVER-SC-http-source-failure'> from 'VC-http-source-failure' to UseCases::'UC-update'::'SC-http-source-failure';
    verification def <'VC-http-untrusted'> 'Reject untrusted retrieved content' {
        subject target : UpdateClient;
        objective { verify consumerVerification; }
        doc Acceptance /* The client rejects the content before use; retrieval alone does not count as verification. */
        doc Method /* Test */
        doc Setup /* Admitted cache miss; package content that conflicts with authenticated publisher metadata. */
        doc Action /* Retrieve the altered content and attempt client verification. */
    }
    dependency <'COVER-SC-http-untrusted'> from 'VC-http-untrusted' to UseCases::'UC-update'::'SC-http-untrusted';
    verification def <'VC-http-cache-untrusted'> 'Reject untrusted cached content' {
        subject target : UpdateClient;
        objective { verify consumerVerification; }
        doc Acceptance /* The client rejects the content before use and the source records zero new requests. */
        doc Method /* Test */
        doc Setup /* Admitted request; altered content already in a fresh cache; authenticated publisher metadata. */
        doc Action /* Retrieve the cached object and attempt client verification while counting source requests. */
    }
    dependency <'COVER-SC-http-cache-untrusted'> from 'VC-http-cache-untrusted' to UseCases::'UC-update'::'SC-http-cache-untrusted';
}
