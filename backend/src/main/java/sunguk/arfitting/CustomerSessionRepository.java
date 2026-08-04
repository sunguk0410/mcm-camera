package sunguk.arfitting;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface CustomerSessionRepository extends JpaRepository<CustomerSession, Long> {
    Optional<CustomerSession> findByCameraIdAndTrackIdAndStatus(
            String cameraId,
            Long trackId,
            SessionStatus status
    );
}
