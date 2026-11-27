package NetworkingDesign {
    doc /*
       Mapped network provider; logical transports and physical attachments retain their platform
       identities. Detailed networking design remains in docs/01-architecture/05-networking. This is a
       map to the existing shared identity, not a new component or detailed implementation claim.
    */
    public import Platform::platform::'Guest network attachment';
}
