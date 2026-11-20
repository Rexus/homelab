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
