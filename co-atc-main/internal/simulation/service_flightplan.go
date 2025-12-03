package simulation

import (
	"github.com/yegors/co-atc/internal/adsb"
)

// GetFlightPlan returns the flight plan for a simulated aircraft
func (s *Service) GetFlightPlan(hex string) []adsb.Position {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	if aircraft, exists := s.aircraft[hex]; exists {
		return aircraft.FlightPlan
	}
	return nil
}
