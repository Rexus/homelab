package ProxyDesign {
    part def <'DEF-proxy'> PolicyProxy {
        port listener : TransferPort;
        port outbound : TransferPort;
        port cacheAccess : TransferPort;
        doc <'DOC-proxy-contract'> 'Contract obligations'
            /* Admit by client, destination and port before forwarding or cache lookup.
               Reject disallowed requests without contacting the source or reading cached content.
               Forward encrypted tunnels without payload inspection.
               Cache eligible HTTP responses only; a cache hit conveys no release approval. */
    }
}
