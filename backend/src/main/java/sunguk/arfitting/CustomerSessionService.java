package sunguk.arfitting;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional
public class CustomerSessionService {

    private final CustomerSessionRepository customerSessionRepository;

    public CustomerSessionResponse createOrGet(
            CreateCustomerSessionRequest request
    ) {
        CustomerSession session = customerSessionRepository
                .findByCameraIdAndTrackIdAndStatus(
                        request.cameraId(),
                        request.trackId(),
                        SessionStatus.ACTIVE
                )
                .map(existing -> {
                    existing.updateLastSeen();
                    return existing;
                })
                .orElseGet(() ->
                        customerSessionRepository.save(
                                new CustomerSession(
                                        request.cameraId(),
                                        request.trackId()
                                )
                        )
                );

        return CustomerSessionResponse.from(session);
    }
}
