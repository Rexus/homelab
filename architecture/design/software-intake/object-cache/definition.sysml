package CacheDesign {
    item def <'DEF-cached-content'> CachedContent :> Transfer {
        doc /* Stored response data and associated cache metadata. Disposable copies, not an executing
               component, authoritative retention, or evidence of publisher trust. */
    }
    part def <'DEF-cache'> DisposableCache {
        port access : TransferPort;
        item <'DEF-cache-contents'> contents[0..*] : CachedContent;
        doc /* Storage responsibility holding zero or more cached objects. Selected virtual disks
               realize this part; the content remains a separate item feature. */
    }
}
