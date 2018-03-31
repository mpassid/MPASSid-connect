# MPASSid Auth Connector Service
![](http://img.shields.io/:license-mit-blue.svg)
![](https://travis-ci.org/mpassid/MPASSid-connect.svg?branch=master)

The Connector Service is used for adding authentication methods for users in the system.New user is invited to the system as Invitee. The invitation happens by the Invitator. Invitator must be existing user in the system. Each user can have multiple authentication methods in use from the set of supported methods. The Connector Service is using Auth Proxy to authenticate users. The connections are stored in the Auth Data Service. The Connector Service does not have any interfaces. It is used be the users with a browser.


## Contribution

Developer information and more detailed documentation will be available in <http://www.mpass.fi> 

## Quick install guide
Currently ansible scripts only support single server installation. All the components are installed  in one server (database, httpd, MPASSid data component) 
### Prerequisites

RedHat/CentOS 7 server (ie. virtual machine) with root privileges.
You can use the Vagrant configuration provided. 

### Installation steps
##### 1 Download just the ansible scripts (**ansible.tar.gz**) or clone this entire repository and use Vagrant to provision virtual server.

##### 2 Configure installation parameters in ...roles/vars/secure.yml. Parametters are

| Parameter | Description| 
|----------| -----------|
| app_root  |Directory where applicattion is installed|
| git_repo | Temporary directory used during installation|
| db_name | PostgreSQL database name |
| db_user | PostgreSQL database username |
| db_pass | PostrgeSQL pasword for username |
| db_serv | IP/FQDN from PostgreSQL database server |
| ServerName | Apache configuration Servername |
| ServerAdmin | Apache admin contact email |
| SSLCertificateFile | Apache path to SSL certificate |
| SSLCertificateKeyFile | Apache path to SSL private key |

##### 3  Run Vagrant
`$ vagrant up `

If you prefer to use just the ansible scripts you can run them for example in localhoat as follows: 

`$ sudo  ansible-playbook -i "localhost," -c local mpass-data.yml`

##### 4 Create Django administrator account
Activate python virtual environment.

`$ cd {app_root}`

`$ source env/bin/activate`

Change to mpass-data home and run Django management utils

 `$ cd mpass-data`

 `$ python manage.py createsuperuser `




### End
