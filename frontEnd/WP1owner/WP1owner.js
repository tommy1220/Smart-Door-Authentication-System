var apigClient = apigClientFactory.newClient({
    accessKey: '',
    secretKey: ''
});


//?faceId=shabi2&file_name=file_name2&bucket_name=bucket_name2&time_stamp=time_stamp2

//S3 url: S3_URL + '/' + file_name
//ObjectKey: 图片名
//“photos”: [
//		{
//			“objectKey”: “my-photo.jpg”, 
//			“bucket”: “my-photo-bucket”, 
//			“createdTimestamp”:“2018-11-05T12:40:02” 
//		}
//]

//temp_WP1_URL = WP1_URL + '#' + faceId + '&' + file_name + '&' + bucket_name + '&' + time_stamp
//temp_S3_URL = S3_URL + '/' + file_name
//<img src=\"""" + temp_S3_URL + """\", alt=\"jojo\" width="640px", height="480px"></div>
//-------------------------------------main code-----------------------------



//get value from url
var faceId = urlValue("faceId");
var objectKey = urlValue("file_name");//file_name is objectKey(name of picture)
var bucket = urlValue("bucket_name");
var time_stamp = urlValue("time_stamp");

console.log(faceId, objectKey, bucket, time_stamp);

//submit form use POST 
function submitForm(){


	var ifDeny = document.getElementById("denyAccess").checked

	var access_denied = 0;//1 - deny, 0 - allow
	if(ifDeny){
		access_denied = 1;
	}
	else{
		access_denied = 0;
	}


	if(isValid()){
		var name = document.getElementById("name").value;
		var phoneNumber = document.getElementById("phoneNumber").value;
		phoneNumber = phoneNumber.replace(/[^0-9]/gi,'');//delete space,() and -. change into 10 digits
		var body = {
			"name" : name,
			"faceId" : faceId,
			"phoneNumber" : phoneNumber,
			"objectKey" : objectKey,
			"bucket" : bucket,
			"createdTimestamp": time_stamp,
			"access_denied": String(access_denied)
		};
		var params = {};
  		var additionalParams = {};

  		apigClient.wP1ownerPost(params, body, additionalParams)
	  		.then(function(result){
	      		console.log(result);
	    	}).catch( function(result){
	    		console.log(result);
	    });
	}
}

//check if name&phone is valid
function isValid(){
	var name = document.getElementById("name").value;
	var phoneNumber = document.getElementById("phoneNumber").value;
	var ifDeny = document.getElementById("denyAccess").checked;
	//(111) 111 1111, () and space is optional
	//(111)-111-1111
	//(111).111.1111
	var phoneRegExpress = /^[(]{0,1}[0-9]{3}[)]{0,1}[-\s\.]{0,1}[0-9]{3}[-\s\.]{0,1}[0-9]{4}$/;

	if(!ifDeny){
		if(name == '' || phoneNumber == ''){
			alert("Please fill in all the fields!");
			return false;
		}
		else if(!phoneNumber.match(phoneRegExpress)){
			alert("Invalid phone number!");
			return false;
		}
		else{
			return true;
		}
	}
	else{
		return true;
	}
}

//get value from url
function urlValue(name){
	var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)", "i");      
	var r = window.location.search.substr(1).match(reg);  //获取url中"?"符后的字符串并正则匹配    
	var context = "";      
	if (r != null)           
		context = r[2];      
	reg = null;      
	r = null;      
	return context == null || context == "" || context == "undefined" ? "" : context;
}