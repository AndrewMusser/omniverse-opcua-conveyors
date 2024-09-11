
TYPE
	Conveyor_Io_typ : 	STRUCT 
		diPhotoeye1 : BOOL;
		diPhotoeye2 : BOOL;
		aoSpeed : REAL;
	END_STRUCT;
	Conveyor_Out_typ : 	STRUCT 
		readyToSend : BOOL;
		readyToReceive : BOOL;
		transferComplete : BOOL;
	END_STRUCT;
	Conveyor_In_typ : 	STRUCT 
		upstreamReadyToSend : BOOL;
		downstreamReadyToReceive : BOOL;
		beltSpeed : REAL;
	END_STRUCT;
	Conveyor_Internal_typ : 	STRUCT 
		state : CONVEYOR_ST_enum;
	END_STRUCT;
	CONVEYOR_ST_enum : 
		(
		CONVEYOR_ST_INIT,
		CONVEYOR_ST_READY_TO_RECEIVE,
		CONVEYOR_ST_RECEIVING,
		CONVEYOR_ST_POSITION,
		CONVEYOR_ST_READY_TO_SEND,
		CONVEYOR_ST_SENDING
		);
	Conveyor_typ : 	STRUCT 
		in : Conveyor_In_typ;
		out : Conveyor_Out_typ;
		io : Conveyor_Io_typ;
		internal : Conveyor_Internal_typ;
	END_STRUCT;
END_TYPE
