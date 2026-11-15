# Build from tier-1/scripts. Supply a vetted digest-pinned base containing Python 3,
# Git, OpenSSH (ssh-keygen for SSH commit signing), and the private Git CA trust.
# docker build --build-arg BASE_IMAGE=<approved-image>@sha256:<digest> -f promotion/Dockerfile .
# Publish the result through the existing intake path and use its immutable digest in role inputs.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER 0
RUN python3 --version && git --version && command -v ssh-keygen
COPY promote.py promotion_git.py promotion_flux.py promotion_authority.py promotion_client.py /worker/
COPY promotion/git-askpass.py /worker/promotion/git-askpass.py
RUN chmod 0555 /worker/promote.py /worker/promotion/git-askpass.py
ENV PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
USER 65532:65532
WORKDIR /tmp
ENTRYPOINT ["python3", "/worker/promote.py"]
