package sunguk.arfitting;

public record CustomerSessionResponse(
        Long customerSessionId,
        String cameraId,
        Long trackId,
        String status
) {
    public static CustomerSessionResponse from(
            CustomerSession session
    ) {
        return new CustomerSessionResponse(
                session.getId(),
                session.getCameraId(),
                session.getTrackId(),
                session.getStatus().name()
        );
    }
}
