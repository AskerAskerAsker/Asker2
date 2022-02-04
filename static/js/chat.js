var MOBILE = /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent) || (/Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.platform));

var success_str = 'kfO1wMuva3hNgh0AhIviPyhEGyoRjDdX';
var new_activity_str = 'bDvziM9fOa85xovJ';
var counterpart_msgs_str = 'hmiJEd3j';
var new_deletions_str = 'JEyr8mg0';

var refresh_time = 400;
var extra_req = 0;
var last_viewed = -1;

var chatbox = document.getElementById('chatbox');

function move_vchk(to) {
	var destination = document.getElementById(to);
	if (destination.parentElement.className == 'rmsg') {
		document.getElementById(to).appendChild(document.getElementById('vchk'));
	}
}

function mark_viewed() {
	var msgs = document.getElementsByClassName('msg');
	if (msgs.length > 0) {
		var last_msg_el = msgs[msgs.length-1];
	} else {
		var last_msg_el = 0;
	}
	if (!last_msg_el) { console.log(''); return 0; }
	if (last_msg_el.getElementsByClassName('lmsg')) {	
		var last_msg = last_msg_el.getAttribute('data-id');
		if (last_viewed != last_msg) {
			$.ajax({
			  type: 'GET',
			  url: '/markviewed',
			  data: {
				  c: CID, 
				  type: 'new', 
				  m: last_msg,
			  },
			  success: function(data) {
				  document.title = 'Mensagens';
			  }
			});
			last_viewed = last_msg;
		}
	}
	return 0;
}

function load_old() {
	var msgs = document.getElementsByClassName('msg');
	var btn = document.getElementById('load-old');
	btn.disabled = true;
	if (msgs.length > 0) {
		var last_msg = msgs[0].getAttribute('data-id');
	} else {
		var last_msg = 0;
	}
	
	$.ajax({
		type: 'GET',	
		url: '/loadmsgs',
		data: {
			c: CID, 
			type: 'old', 
			last: last_msg,
		},
		success: function(data) {
			if (data.includes(new_activity_str)) {
				var msgl = document.getElementById('msg-l');
				msgl.innerHTML = data + msgl.innerHTML;
			}
			btn.disabled = false;
			if (data.includes(success_str) && !data.includes(new_activity_str)) {
				btn.remove();
			}
		},
		error: function(data) {
			btn.disabled = false;
		}
	});			
}
function load_new() {
	var msgs = document.getElementsByClassName('msg');
	if (msgs.length > 0) {
		var last_msg = msgs[msgs.length-1].getAttribute('data-id');
	} else {
		var last_msg = 0;
	}
	
	$.ajax({
	  type: 'GET',
	  url: '/loadmsgs',
	  data: {
		  c: CID, 
		  type: 'new', 
		  last: last_msg,
		  lkv: last_viewed, 
	  },
	  success: function(data) {
		  if (data.includes(new_activity_str)) {
			  refresh_time = 400;
		  } else {
			refresh_time = refresh_time + Math.floor(refresh_time/3);
		  }
		  if (extra_req <= 0) {
			setTimeout("load_new()", refresh_time);
		  } else {
			extra_req = extra_req - 1;
		  }
		  if (data.includes(new_activity_str) || data.includes(new_deletions_str)) {
			var msgl = document.getElementById('msg-l');
			msgl.innerHTML = msgl.innerHTML + data;
		  }
		  if (data.includes(new_activity_str)) {
			chatbox.scrollTop = chatbox.scrollHeight;
			if (data.includes(counterpart_msgs_str)) {
				document.title = '(Novas Mensagens) Mensagens';
			}
			var last_viewed_el = document.getElementsByClassName('last_viewed');
			if (last_viewed_el) {
				var new_last_viewed = last_viewed_el[last_viewed_el.length-1].value;
				if (new_last_viewed > last_viewed) {
					move_vchk('m-' + new_last_viewed);
					last_viewed = new_last_viewed;
				}
			}
		  }
		  if (data.includes(new_deletions_str)) {
			var new_deleted = document.getElementsByClassName('d_msg');
			for (var i = new_deleted.length-1; i >= 0 ; i--) {
				var mid = new_deleted[i].value;
				var del_el = document.getElementById('m-' + mid).getElementsByClassName('mtxt')[0];
				if (del_el.style.color != 'rgb(136, 136, 136)') {
					del_el.innerHTML = '[Apagada]';
					del_el.style.color = '#888';
				}
				new_deleted[i].remove();
			}
		  }
	  }
	});
}

function add_img() {
	var text = document.getElementById('upload-photo-text');
	var delete_photo_icon = document.getElementById('delete-photo-icon');
	var input = document.getElementById('upload-photo');
	text.innerText = input.value.slice(12);
	delete_photo_icon.style.display = 'inline';
}
function rm_img() {
	var delete_photo_icon = document.getElementById('delete-photo-icon');
	var input = document.getElementById('upload-photo');
	var text = document.getElementById('upload-photo-text');
	delete_photo_icon.style.display = 'none';
	text.innerText = '';
	input.value = null;
}
function send_img() {
	document.getElementById("send-btn").disabled = true;
	file = document.getElementById('upload-photo').files[0];
	var fd = new FormData();
	fd.append('csrfmiddlewaretoken', CSRF_TOKEN);
	fd.append('c', CID);
	fd.append('file', file);
	$.ajax({
		url: "/sendmsg",
		method: "POST",
		cache:false,
		processData: false,
		contentType: false,
		data: fd,
		success: function(data) {
			document.getElementById("send-btn").disabled = false;
			rm_img();
			if (refresh_time > 1200000) {
				location.reload();
			} else if (refresh_time > 4000) {
				load_new();
				extra_req = extra_req + 1;
			}
			refresh_time = 400;
		},
		error: function() {
			document.getElementById('send-btn').innerHTML = "Erro ao enviar";
		}
	});
}
function send_msg() {
	var img = document.getElementById('upload-photo');
	if (img.value) {
		var form = document.getElementById('img-form');
		send_img();
		return 0;
	}

	var content = document.getElementById('msg_txtarea').value;
	if (content.length == 0) { return 0; }
	document.getElementById('send-btn').disabled = true;
	
	$.ajax({
	  type: 'POST',
	  url: '/sendmsg',
	  data: {
		  csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
		  c: CID, 
		  text: content, 
	  },
	  success: function(data) {
		  if (data == 'Proibido') {
			document.getElementById('send-btn').disabled = false;
		  }
		  if (refresh_time > 1200000) {
			location.reload();
		  } else if (refresh_time > 2000) {
			load_new();
			extra_req = extra_req + 1;
		  }
		  refresh_time = 400;
		  document.getElementById('msg_txtarea').value = null;
		  document.getElementById('send-btn').disabled = false;
	  },
	  error: function() {
		  document.getElementById('send-btn').innerHTML = "Erro ao enviar";
	  }
	});
}

function toggle_options(el) {
	var op = el.getElementsByClassName('options')[0];
	if (op.style.display == 'none') {
		op.style.display = 'flex';
	} else {
		op.style.display = 'none';				
	}
}
function msgrm(msg_id) {
	$.ajax({
	  type: 'GET',
	  url: '/msgrm',
	  data: {
		  c: CID, 
		  m: msg_id,
	  },
	  success: function(data) {
		var del_el = document.getElementById('m-' + msg_id).getElementsByClassName('mtxt')[0];
		del_el.innerHTML = '[Apagada]';
		del_el.style.color = '#888';
	  }
	});
}
function txt_v() {
    var key = window.event.keyCode;
    if (key === 13 && !window.event.shiftKey && !MOBILE) {
        window.event.preventDefault();
		send_msg();
        return false;
    }
    return true;
}

chatbox.scrollTop = chatbox.scrollHeight;
document.getElementById('upload-photo').value = '';  // refresh
document.body.addEventListener('click', mark_viewed, true);
	
setTimeout("load_new()", 1000);