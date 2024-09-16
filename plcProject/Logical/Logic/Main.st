PROGRAM _INIT

	FOR index := 0 TO MAI_CONVEYORS DO
		conveyor[index].in.beltSpeed := 1.3;
	END_FOR
	
	processTimer.PT := T#2.5s;

END_PROGRAM



PROGRAM _CYCLIC

	// Map conveyor outputs to neighboring conveyor inputs. 
	conveyor[0].in.downstreamReadyToReceive := conveyor[1].out.readyToReceive;
	conveyor[0].in.upstreamReadyToSend := TRUE;
	conveyor[1].in.downstreamReadyToReceive := conveyor[2].out.readyToReceive;
	conveyor[1].in.upstreamReadyToSend := conveyor[0].out.readyToSend;	
	conveyor[2].in.downstreamReadyToReceive := conveyor[3].out.readyToReceive;
	conveyor[2].in.upstreamReadyToSend := conveyor[1].out.readyToSend;
	conveyor[3].in.downstreamReadyToReceive := conveyor[4].out.readyToReceive;
	conveyor[3].in.upstreamReadyToSend := conveyor[2].out.readyToSend;
	conveyor[4].in.downstreamReadyToReceive := processTimer.Q;
	conveyor[4].in.upstreamReadyToSend := conveyor[3].out.readyToSend;

	FOR index := 0 TO MAI_CONVEYORS DO
	
		// Reset all output signal cyclically. 
		conveyor[index].out.readyToReceive := FALSE;
		conveyor[index].out.readyToSend := FALSE;
		conveyor[index].out.transferComplete := FALSE;
		conveyor[index].io.aoSpeed := 0;
	
		CASE conveyor[index].internal.state OF
		
			CONVEYOR_ST_INIT:
				IF (conveyor[index].io.diPhotoeye2) THEN
					conveyor[index].internal.state := CONVEYOR_ST_READY_TO_SEND;
				ELSE
					conveyor[index].internal.state := CONVEYOR_ST_READY_TO_RECEIVE;
				END_IF
				
			CONVEYOR_ST_READY_TO_RECEIVE:
				conveyor[index].out.readyToReceive := TRUE;
				IF (conveyor[index].io.diPhotoeye1) THEN
					conveyor[index].internal.state := CONVEYOR_ST_RECEIVING;
				END_IF
				
			CONVEYOR_ST_RECEIVING:
				conveyor[index].out.readyToReceive := TRUE;
				conveyor[index].io.aoSpeed := conveyor[index].in.beltSpeed;
				IF (NOT conveyor[index].io.diPhotoeye1) THEN
					conveyor[index].internal.state := CONVEYOR_ST_POSITION;
				END_IF
				
			CONVEYOR_ST_POSITION:
				conveyor[index].io.aoSpeed := conveyor[index].in.beltSpeed;
				IF (conveyor[index].io.diPhotoeye2) THEN
					IF (conveyor[index].in.downstreamReadyToReceive) THEN
						conveyor[index].internal.state := CONVEYOR_ST_SENDING;
					ELSE
						conveyor[index].internal.state := CONVEYOR_ST_READY_TO_SEND;
					END_IF				
				END_IF
				
			CONVEYOR_ST_READY_TO_SEND:
				conveyor[index].out.readyToSend := TRUE;
				IF (conveyor[index].in.downstreamReadyToReceive) THEN
					conveyor[index].internal.state := CONVEYOR_ST_SENDING;
				END_IF
				
			CONVEYOR_ST_SENDING:
				conveyor[index].out.readyToSend := TRUE;
				conveyor[index].io.aoSpeed := conveyor[index].in.beltSpeed;
				IF (NOT conveyor[index].io.diPhotoeye2) THEN
					conveyor[index].internal.state := CONVEYOR_ST_READY_TO_RECEIVE;
				END_IF
				
		END_CASE
		
	END_FOR
	
	// Handle process logic. 
	processTimer.IN := conveyor[4].out.readyToSend;
	processTimer();
	processActive := processTimer.IN;
	 
END_PROGRAM

