var apigClient = apigClientFactory.newClient({
    accessKey: '',
    secretKey: ''
});



//submit OTP use POST 
function submitOTP(){

	if(isValid()){
		var OTP = document.getElementById("OTP").value;

		var body = {
			"OTP" : OTP
		};
		var params = {};
  		var additionalParams = {};

  		apigClient.wP2visitorPost(params, body, additionalParams)
	  		.then(function(result){
	      		console.log(result);
	      		let returnMessage = result.data;
	      		alert(returnMessage);
	    	}).catch( function(result){
	    		console.log(result);
	    });
	}
}

//check if OTP is filled
function isValid(){
	var OTP = document.getElementById("OTP").value;
	if(OTP == ""){
		alert("Please fill in your OTP!");
		return false;
	}
	else{
		return true;
	}
}