package sunguk.arfitting;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class CustomerSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String cameraId;

    private Long trackId;

    private LocalDateTime enteredAt;

    private LocalDateTime lastSeenAt;

    @Enumerated(EnumType.STRING)
    private SessionStatus status;

    public CustomerSession(String cameraId, Long trackId) {
        this.cameraId = cameraId;
        this.trackId = trackId;
        this.enteredAt = LocalDateTime.now();
        this.lastSeenAt = LocalDateTime.now();
        this.status = SessionStatus.ACTIVE;
    }

    public void updateLastSeen() {
        this.lastSeenAt = LocalDateTime.now();
    }

    public void close() {
        this.status = SessionStatus.CLOSED;
    }
}
