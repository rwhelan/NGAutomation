package main

import (
//	"fmt"
	"os"
	"io/ioutil"
	"encoding/json"
	"syscall"
)

var distFiles = []string {
	"/etc/redhat-release",
	"/etc/lsb-release",
	"/etc/fedora-release",
	"/etc/slackware-release",
	"/etc/debian_release",
	"/etc/debian_version",
	"/etc/mandrake-release",
	"/etc/yellowdog-release",
	"/etc/sun-release",
	"/etc/release",
	"/etc/gentoo-release",
	"/etc/UnitedLinux-release",
	"/etc/SUSE-release",
	"/etc/SuSE-release",
}

type metadata map[string]string

func (m metadata) gethostname() (error) {
	hostn, err := os.Hostname()
	if err != nil {
		return err
	}
	m["hostname"] = hostn
	return nil
}

func (m metadata) getosrelease() (error) {
	for _, distf := range distFiles {
		release, err := ioutil.ReadFile(distf)
		if err == nil {
			if release[len(release)-1] == 10 {
				m["osrelease"] = string(release[0:len(release)-1])
			} else {
				m["osrelease"] = string(release)
			}
			return nil
		}
	}
	m["osrelease"] = "Unknown"
	return nil
}

func (m metadata) getplatform() (error) {
	uts := new(syscall.Utsname)
	err := syscall.Uname(uts)
	if err != nil {
		return err
	}

	s := make([]byte, len(uts.Machine))
	i := 0
	for ; i < len(uts.Machine); i++ {
		if uts.Machine[i] == 0 {
			break
		}
		s[i] = uint8(uts.Machine[i])
	}
	m["platform"] = string(s[0:i])
	return nil
}

func metadataContructor() (metadata) {
	md := make(metadata)
	md.gethostname()
	md.getosrelease()
	md.getplatform()
	return md
}

func main() {
	metad := metadataContructor()

	// metad['timestamp'] = yadda-yadda-yadda

	output, _ := json.MarshalIndent(metad, "", "    ")
	os.Stdout.Write(output)
}
